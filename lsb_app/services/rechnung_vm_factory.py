# lsb_app/services/rechnung_vm_factory.py
from datetime import date, time
from lsb_app.viewmodels.rechnung_vm import RechnungVM, LeistungVM
from lsb_app.models import RechnungsadressModus
from lsb_app.extensions import db
from markupsafe import Markup
from decimal import Decimal, ROUND_HALF_UP
import holidays
from lsb_app.services.entfernungsrechner import berechne_entfernung

def wegegeld_berechnen(dist, uhr) -> str:
    if time(8, 0) <= uhr <= time(20, 0):
        if dist < 2: return "< 2 km (tags)", "3,58"
        if dist < 5: return "2 - 5 km (tags)", "6,65"
        if dist < 10: return "5 - 10 km (tags)", "10,23"
        if dist < 25: return "10 - 25 km (tags)", "15,34"
        return "> 25 km (0,26 €/km)", f"{2 * dist * 0.26:.2f}".replace(".", ",")
    else:
        if dist < 2: return "< 2 km (nachts)", "7,16"
        if dist < 5: return "2 - 5 km (nachts)", "10,23"
        if dist < 10: return "5 - 10 km (nachts)", "15,34"
        if dist < 25: return "10 - 25 km (nachts)", "25,56"
        return "> 25 km (0,26 €/km)", f"{2 * dist * 0.26:.2f}".replace(".", ",")
    
def erstelle_anschrift_html_bestattungsinstitut(auftrag) -> str:
    inst = auftrag.bestattungsinstitut
    if not inst:
        #TODO Fehlerbehandlung
        return "<p>Bestattungsinstitut</p>"

    modus = inst.rechnungadress_modus
    adr = inst.adresse

    inst_block = f"{inst.firmenname}<br>{adr.strasse} {adr.hausnummer}<br>{adr.plz} {adr.ort}"

    if modus == RechnungsadressModus.INSTITUT:
        return inst_block
    elif modus == RechnungsadressModus.INSTITUT_WEITERLEITUNG:
        header = "Zur Weiterleitung an die Angehörigen"
        return f"{header}<br>{inst_block}"
    elif modus == RechnungsadressModus.ANGEHOERIGE:
        #TODO Fehlerbehandlung falls kein Angehöriger vorhanden
        return erstelle_anschrift_html_angehoeriger(auftrag)
    
    #TODO Fehlerbehandlung
    return "<p>Bestattungsinstitut</p>"

def erstelle_anschrift_html_angehoeriger(auftrag) -> str:
        angehoeriger = auftrag.patient.angehoerige[0]
        adr_ang = angehoeriger.adresse
        anschrift_html = f"{angehoeriger.name}, {angehoeriger.vorname}<br>{adr_ang.strasse} {adr_ang.hausnummer}<br>{adr_ang.plz} {adr_ang.ort}"
        return anschrift_html

def build_rechnung_vm(auftrag, cfg, rechnungsdatum: date, rechnungsart: str) -> RechnungVM:
    
    val = getattr(auftrag.kostenstelle, "value", auftrag.kostenstelle)
    kostenstelle = (val or "").lower()

    if kostenstelle == "angehörige":
        anschrift_html = erstelle_anschrift_html_angehoeriger(auftrag)
    elif kostenstelle == "behörde":
        behoerde = auftrag.behoerden[0]
        adr_beh = behoerde.adresse
        anschrift_html = f"{behoerde.name}<br>{adr_beh.strasse} {adr_beh.hausnummer}<br>{adr_beh.plz} {adr_beh.ort}"
    elif kostenstelle == "bestattungsinstitut":
        anschrift_html = erstelle_anschrift_html_bestattungsinstitut(auftrag)
    else:
        anschrift_html = "<p>unbekannt</p>"
    
    leistungen = []
    leistungen.append(LeistungVM(
        kurz="GOÄ-Nr. 101",
        beschreibung="Untersuchung eines/r Toten einschließlich Feststellung des Todes / "
            "Ausstellung eines Leichenschauscheines",
        betrag="165,77"
        )
    )
    leistungen.append(LeistungVM(
        kurz="Auslagen",
        beschreibung="Formular Todesbescheinigung + Materialien",
        betrag="3,50"
    ))

    uhrzeit = auftrag.auftragsuhrzeit

    if (time(20, 0) <= uhrzeit < time(22, 0)) or (time(6, 0) < uhrzeit <= time(8, 0)):
        leistungen.append(LeistungVM(
            kurz="Zuschlag F",
            beschreibung="Leistungszeit 20-22 Uhr oder 6-8 Uhr",
            betrag="15,15"
        ))
    elif uhrzeit >= time(22, 0) or uhrzeit <= time(6, 0):
        leistungen.append(LeistungVM(
            kurz="Zuschlag G",
            beschreibung="Leistungszeit 22-6 Uhr",
            betrag="26,23"
        ))
    
    datum = auftrag.auftragsdatum

    if datum.weekday() >= 5 or datum in holidays.Germany(prov="BY"):
        leistungen.append(LeistungVM(
            kurz="Zuschlag H",
            beschreibung="Leistung an Samstagen, Sonntagen oder Feiertagen",
            betrag="19,82"
        ))
    
    fahrstrecke = None

    if not auftrag.auftragsadresse.distanz:
        try:
            strasse = f"{auftrag.auftragsadresse.strasse} {auftrag.auftragsadresse.hausnummer}"
            plz = auftrag.auftragsadresse.plz
            ort = auftrag.auftragsadresse.ort
            fahrstrecke = berechne_entfernung(strasse=strasse,
                                    plz=plz,
                                    ort=ort)
            
            if fahrstrecke is not None:
                auftrag.auftragsadresse.distanz = fahrstrecke
                db.session.add(auftrag.auftragsadresse)
                db.session.commit()

        except Exception as e:
            print(f"Fehler: {e}")
    else:
        fahrstrecke = auftrag.auftragsadresse.distanz

    wg_text, wg_betrag = wegegeld_berechnen(fahrstrecke, uhrzeit)

    leistungen.append(LeistungVM(
        kurz="Wegegeld",
        beschreibung=wg_text,
        betrag=wg_betrag
    ))

    if auftrag.mehraufwand:
        leistungen.append(LeistungVM(
            kurz="GOÄ-Nr. 102",
            beschreibung="Zuschlag bei besonderen Todesumständen",
            betrag="27,63"
        ))

    summe = sum(Decimal(e.betrag.replace(",", ".")) for e in leistungen).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    summe_str = str(summe).replace(".", ",")

    # rechnungsart = "TEST"
    
    return RechnungVM(
        auftrag_id=auftrag.id,
        auftragsnummer=auftrag.auftragsnummer,

        rechnungsart=rechnungsart,

        rechnungsdatum=rechnungsdatum,
        auftragsdatum=auftrag.auftragsdatum,

        patient_name=auftrag.patient.name,
        patient_vorname=auftrag.patient.vorname,
        patient_geburtsdatum=auftrag.patient.geburtsdatum,
        patient_geschlecht=auftrag.patient.geschlecht,

        anschrift_html=Markup(anschrift_html),

        leistungen=leistungen,

        summe_str=summe_str,

        config={
                "COMPANY_NAME": cfg["COMPANY_NAME"],
                "COMPANY_ROLE": cfg["COMPANY_ROLE"],
                "COMPANY_ADDRESS": cfg["COMPANY_ADDRESS"],
                "COMPANY_PHONE": cfg["COMPANY_PHONE"],
                "COMPANY_EMAIL": cfg["COMPANY_EMAIL"],
                "BANK_IBAN": cfg["BANK_IBAN"],
                "BANK_BIC": cfg["BANK_BIC"],
                "TAX_NUMBER": cfg["TAX_NUMBER"],
            },
    )
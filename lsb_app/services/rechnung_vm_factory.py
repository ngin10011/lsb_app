# lsb_app/services/rechnung_vm_factory.py
from datetime import date, time
from lsb_app.viewmodels.rechnung_vm import RechnungVM, LeistungVM
from markupsafe import Markup
from decimal import Decimal, ROUND_HALF_UP

def build_rechnung_vm(auftrag, cfg, anschrift_html: str, rechnungsdatum: date) -> RechnungVM:
    
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

    summe = sum(Decimal(e.betrag.replace(",", ".")) for e in leistungen).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    summe_str = str(summe).replace(".", ",")
    
    return RechnungVM(
        auftrag_id=auftrag.id,
        auftragsnummer=auftrag.auftragsnummer,

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
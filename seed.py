# seed.py

from datetime import date, time, timedelta
import random
from dataclasses import dataclass

from faker import Faker

from sqlalchemy import func, cast, Integer

from lsb_app.extensions import db
from lsb_app.models import (Patient, Adresse, Auftrag, Verlauf,
        Bestattungsinstitut, Behoerde, Angehoeriger)
from lsb_app.models.enums import (
    GeschlechtEnum,
    KostenstelleEnum,
    AuftragsStatusEnum,
)

# Deutscher Faker (für Namen / Adressen)
fake = Faker("de_DE")


def create_address() -> Adresse:
    """
    Erzeugt eine realistisch aussehende Adresse.
    Die Distanz wird absichtlich zufällig gesetzt, damit
    kein externer Distanz-Service nötig ist.
    """
    addr = Adresse(
        strasse=fake.street_name(),
        hausnummer=str(random.randint(0, 80)),
        plz=fake.postcode(),
        ort=fake.city(),
        # Distanz absichtlich direkt gesetzt (0–30 km),
        # damit später kein ORS/Nominatim-Call nötig ist.
        distanz=random.randint(1, 30),
    )
    db.session.add(addr)
    db.session.flush()  # addr.id verfügbar
    return addr

def create_patient() -> Patient:
    patient = Patient(
        name=fake.last_name(),
        vorname=fake.first_name(),
        geburtsdatum=fake.date_of_birth(minimum_age=40, maximum_age=95),
        geschlecht=random.choice(list(GeschlechtEnum)),
        meldeadresse=create_address(),
    )
    db.session.add(patient)
    db.session.flush()
    return patient

@dataclass(frozen=True)
class AngehoerigerHas:
    name: bool = False
    vorname: bool = False
    geschlecht: bool = False
    adresse: bool = False
    telefonnummer: bool = False
    email: bool = False
    verwandtschaftsgrad: bool = False

def create_angehoeriger(
    patient,
    *,
    has: AngehoerigerHas = AngehoerigerHas(),
    **overrides
):
    data = {}

    if has.name:
        data["name"] = overrides.get("name", fake.last_name())

    if has.vorname:
        data["vorname"] = overrides.get("vorname", fake.first_name())

    if has.geschlecht:
        data["geschlecht"] = overrides.get(
            "geschlecht", random.choice(list(GeschlechtEnum))
        )

    if has.adresse:
        data["adresse"] = overrides.get("adresse", create_address())

    if has.telefonnummer:
        data["telefonnummer"] = overrides.get(
            "telefonnummer", fake.phone_number()
        )

    if has.email:
        data["email"] = overrides.get("email", "engincakir19@gmail.com")

    if has.verwandtschaftsgrad:
        data["verwandtschaftsgrad"] = overrides.get(
            "verwandtschaftsgrad", fake.word()
        )

    angehoeriger = Angehoeriger(patient=patient, **data)
    db.session.add(angehoeriger)
    db.session.flush()
    return angehoeriger

def create_bestattungsinstitut() -> Bestattungsinstitut:
    bestattungsinstitut = Bestattungsinstitut(
        kurzbezeichnung=fake.company(),
        firmenname=fake.company(), #später beides gleich setzen
        adresse=create_address(),
        email='engincakir19@gmail.com',
    )
    db.session.add(bestattungsinstitut)
    db.session.flush()
    return bestattungsinstitut

def create_behoerde() -> Behoerde:
    behoerde = Behoerde(
        name=fake.company(),
        adresse=create_address(),
        email='engincakir19@gmail.com',
    )
    db.session.add(behoerde)
    db.session.flush()
    return behoerde

@dataclass(frozen=True)
class VerlaufHas:
    datum: bool = True
    ereignis: bool = True
    auftrag_id: bool = True

def create_verlauf(
        auftrag_id: int,
        *,
        has: VerlaufHas = VerlaufHas(),
        **overrides
    ) -> Verlauf:

    data = {}

    if has.datum:
        data["datum"] = overrides.get("datum", fake.date())

    if has.ereignis:
        data["ereignis"] = overrides.get("ereignis", "Ereignis stattgefunden")

    verlauf = Verlauf(auftrag_id=auftrag_id, **data)
    db.session.add(verlauf)
    db.session.flush()
    return verlauf

def _next_auftragsnummer() -> int:
    max_nr = db.session.query(func.max(Auftrag.auftragsnummer)).scalar() or 1000
    return max_nr + 1

@dataclass(frozen=True)
class AuftragHas:
    # Pflichtfelder: default TRUE (werden gesetzt)
    auftragsdatum: bool = True
    auftragsuhrzeit: bool = True
    kostenstelle: bool = True
    mehraufwand: bool = True
    status: bool = True
    patient_id: bool = True
    auftragsadresse_id: bool = True
    auftragsnummer: bool = True

    # Optional: default FALSE
    bemerkung: bool = False
    wait_due_date: bool = False
    is_inquired: bool = False

    # Optional: Relationships statt FK (wenn du das mal brauchst)
    patient: bool = False
    auftragsadresse: bool = False
    bestattungsinstitut: bool = False
    bestattungsinstitut_id: bool = False

def create_auftrag(*, has: AuftragHas = AuftragHas(), **overrides) -> Auftrag:
    data: dict = {}

    # ---------- Pflicht-FKs: müssen kommen ----------
    # Entweder patient_id ODER patient (Relationship) – je nachdem, was du aktivierst.
    if has.patient_id:
        if "patient_id" not in overrides:
            raise ValueError("create_auftrag: patient_id ist Pflicht (als Override übergeben).")
        data["patient_id"] = overrides["patient_id"]

    if has.auftragsadresse_id:
        if "auftragsadresse_id" not in overrides:
            raise ValueError("create_auftrag: auftragsadresse_id ist Pflicht (als Override übergeben).")
        data["auftragsadresse_id"] = overrides["auftragsadresse_id"]

    # ---------- Pflichtfelder: bekommen Defaults ----------
    if has.auftragsdatum:
        data["auftragsdatum"] = overrides.get("auftragsdatum", fake.date_between(start_date='-2w'))

    if has.auftragsuhrzeit:
        # Sekunden ok, Mikrosekunden weg
        data["auftragsuhrzeit"] = overrides.get(
            "auftragsuhrzeit",
            fake.time(),
        )

    if has.kostenstelle:
        data["kostenstelle"] = overrides.get(
            "kostenstelle",
            random.choice(list(KostenstelleEnum)),
        )

    if has.mehraufwand:
        data["mehraufwand"] = overrides.get("mehraufwand", False)

    if has.status:
        data["status"] = overrides.get("status", random.choice(list(AuftragsStatusEnum)))

    if has.auftragsnummer:
        data["auftragsnummer"] = overrides.get("auftragsnummer", _next_auftragsnummer())

    # ---------- Optionales ----------

    if has.bemerkung:
        data["bemerkung"] = overrides.get("bemerkung", None)

    if has.wait_due_date:
        data["wait_due_date"] = overrides.get("wait_due_date", None)

    if has.is_inquired:
        data["is_inquired"] = overrides.get("is_inquired", False)

    # ---------- Optional: Relationships statt FK ----------
    # (nur nutzen, wenn du wirklich lieber Objekte statt IDs übergibst)
    if has.patient:
        if "patient" not in overrides:
            raise ValueError("create_auftrag: has.patient=True, aber kein patient=... übergeben.")
        data["patient"] = overrides["patient"]

    if has.auftragsadresse:
        if "auftragsadresse" not in overrides:
            raise ValueError("create_auftrag: has.auftragsadresse=True, aber kein auftragsadresse=... übergeben.")
        data["auftragsadresse"] = overrides["auftragsadresse"]

    if has.bestattungsinstitut:
        data["bestattungsinstitut"] = overrides.get("bestattungsinstitut", None)

    if has.bestattungsinstitut_id:
        data["bestattungsinstitut_id"] = overrides.get("bestattungsinstitut_id", None)

    auftrag = Auftrag(**data)
    db.session.add(auftrag)
    db.session.flush()
    return auftrag

def seed_data():
    """
    Erzeugt mehrere Testdatensätze:
    - Adresse
    - Patient
    - Auftrag
    - Verlaufseinträge
    """

    #TODO Auftragsadresse != und == Meldeadresse

    # READY + Kostenstelle Bestattungsinstitut - Angehörige - Behörde
    for _ in range(3):
        patient = create_patient()
        adresse = create_address()
        bestattungsinstitut = create_bestattungsinstitut()

        auftrag = create_auftrag(
            has=AuftragHas(bestattungsinstitut_id=True),
            status=AuftragsStatusEnum.READY,
            kostenstelle=KostenstelleEnum.BESTATTUNGSINSTITUT,
            bestattungsinstitut_id=bestattungsinstitut.id,
            patient_id=patient.id,
            auftragsadresse_id=adresse.id
        )

        create_verlauf(
            auftrag_id=auftrag.id,
            # datum=auftrag.auftragsdatum + timedelta(days=2),
            datum=auftrag.auftragsdatum,
            ereignis="TB erstellt")
        
    # READY + Kostenstelle Angehörige + Angehörige E-Mail, Name, Vorname, Tel-Nr, selbe Adresse (wie Auftrags- und Meldeadresse)
    for _ in range(3):
        patient = create_patient()

        create_angehoeriger(
            patient,
            has=AngehoerigerHas(
                name=True,
                vorname=True,
                email=True,
                telefonnummer=True,
                adresse=True,
            ),
            adresse=patient.meldeadresse,
        )

        auftrag = create_auftrag(
            status=AuftragsStatusEnum.READY,
            kostenstelle=KostenstelleEnum.ANGEHOERIGE,
            patient_id=patient.id,
            auftragsadresse_id=patient.meldeadresse_id
        )

        create_verlauf(
            auftrag_id=auftrag.id,
            datum=auftrag.auftragsdatum,
            ereignis="TB erstellt")
        
    # READY + Kostenstelle Angehörige + Angehörige Tel-Nr, selbe Adresse (wie Auftrags- und Meldeadresse)
    for _ in range(3):
        patient = create_patient()

        create_angehoeriger(
            patient,
            has=AngehoerigerHas(
                telefonnummer=True,
                adresse=True,
            ),
            adresse=patient.meldeadresse,
        )

        auftrag = create_auftrag(
            status=AuftragsStatusEnum.READY,
            kostenstelle=KostenstelleEnum.ANGEHOERIGE,
            patient_id=patient.id,
            auftragsadresse_id=patient.meldeadresse_id
        )

        create_verlauf(
            auftrag_id=auftrag.id,
            datum=auftrag.auftragsdatum,
            ereignis="TB erstellt")
        
    # READY + Kostenstelle Angehörige + Angehörige selber Nachname, Geschlecht, Verwandtschaftsgrad, Tel-Nr, selbe Adresse (wie Meldeadresse) + Meldeadresse != Auftragsadresse
    for _ in range(3):
        patient = create_patient()

        create_angehoeriger(
            patient,
            has=AngehoerigerHas(
                name=True,
                geschlecht=True,
                verwandtschaftsgrad=True,
                telefonnummer=True,
                adresse=True,
            ),
            name=patient.name,
            adresse=patient.meldeadresse,
        )

        auftragsadresse = create_address()

        auftrag = create_auftrag(
            status=AuftragsStatusEnum.READY,
            kostenstelle=KostenstelleEnum.ANGEHOERIGE,
            patient_id=patient.id,
            auftragsadresse_id=auftragsadresse.id,
        )

        create_verlauf(
            auftrag_id=auftrag.id,
            datum=auftrag.auftragsdatum,
            ereignis="TB erstellt")

    # READY + Kostenstelle Behörde - Angehörige
    for _ in range(3):
        patient = create_patient()
        adresse = create_address()
        behoerde = create_behoerde()

        auftrag = create_auftrag(
            has=AuftragHas(bestattungsinstitut_id=True),
            status=AuftragsStatusEnum.READY,
            kostenstelle=KostenstelleEnum.BEHOERDE,
            patient_id=patient.id,
            auftragsadresse_id=adresse.id
        )

        
        auftrag.behoerden.append(behoerde)

        create_verlauf(
            auftrag_id=auftrag.id,
            # datum=auftrag.auftragsdatum + timedelta(days=2),
            datum=auftrag.auftragsdatum,
            ereignis="TB erstellt")

    db.session.commit()

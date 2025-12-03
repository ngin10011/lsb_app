# seed.py

from datetime import date, time
import random

from faker import Faker

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
        distanz=random.randint(0, 30),
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

def create_angehoeriger(patient) -> Angehoeriger:
    angehoeriger = Angehoeriger(
        name=fake.last_name(),
        vorname=fake.first_name(),
        geschlecht=random.choice(list(GeschlechtEnum)),
        adresse=create_address(),
        telefonnummer=fake.phone_number(),
        patient=patient,
    )
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

def create_auftrag(auftragsnummer) -> Auftrag:
    patient=create_patient()
    create_angehoeriger(patient)
    
    auftrag = Auftrag(
        auftragsnummer=auftragsnummer,
        patient=patient,
        auftragsadresse=create_address(),

        auftragsdatum=fake.date_between(start_date='-2w'),
        auftragsuhrzeit=fake.time(),

        kostenstelle=random.choice(list(KostenstelleEnum)),
        mehraufwand=False,
        status=random.choice(list(AuftragsStatusEnum)),   # typischer Startstatus

        bestattungsinstitut=create_bestattungsinstitut(),

        # Optional:
        # bemerkung="Seed-Testauftrag",
        # auftragsnummer=None,
        # bestattungsinstitut_id=None,
    )

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
    # Anzahl Testfälle hier anpassen
    auftragnummer = 1000
    for _ in range(5):
        auftrag = create_auftrag(auftragnummer)
        auftrag.behoerden.append(create_behoerde())
        auftragnummer += 1

    db.session.commit()

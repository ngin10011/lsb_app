# seed.py
import random
from datetime import date, time, timedelta
from faker import Faker
from sqlalchemy.exc import IntegrityError
from models import db, Patient, Adresse, Auftrag, GeschlechtEnum, KostenstelleEnum

def seed_faker(n_addresses=10, n_patients=20, deterministic=True, reset=False):
    """
    Erzeugt Beispiel-Daten:
      - Adressen
      - Patienten (mit Meldeadresse)
      - 1:1 Auftrag pro Patient

    Args:
        n_addresses (int): Anzahl zu erzeugender Adressen
        n_patients (int):  Anzahl zu erzeugender Patienten
        deterministic (bool): Gleiche Zufallsdaten bei jedem Lauf
        reset (bool): Drop+Create aller Tabellen vor dem Seeding
    """
    if deterministic:
        Faker.seed(1234)
        random.seed(1234)

    fake = Faker("de_DE")

    if reset:
        db.drop_all()
        db.create_all()

    # 1) Adressen
    adressen = []
    for _ in range(n_addresses):
        a = Adresse(
            strasse=fake.street_name(),
            hausnummer=fake.building_number(),
            plz=fake.postcode(),
            ort=fake.city()
            # distanz=random.randint(1, 60),
        )
        db.session.add(a)
        adressen.append(a)

    db.session.flush()  # IDs verfügbar machen

    genders = list(GeschlechtEnum)
    kosten = list(KostenstelleEnum)

    # 2) Patienten + Auftrag
    for _ in range(n_patients):
        adr = random.choice(adressen)

        p = Patient(
            name=fake.last_name(),
            geburtsname=(fake.last_name() if random.random() < 0.25 else None),
            vorname=fake.first_name(),
            geburtsdatum=fake.date_between(start_date="-95y", end_date="-1y"),
            geschlecht=random.choice(genders),
            meldeadresse=adr,
        )
        db.session.add(p)
        db.session.flush()  # p.id verfügbar

        a = Auftrag(
            auftragsnummer=fake.unique.random_int(min=0, max=9999),
            auftragsdatum=date.today() - timedelta(days=random.randint(0, 30)),
            auftragsuhrzeit=time(hour=random.randint(7, 20),
                                 minute=random.choice([0, 15, 30, 45])),
            kostenstelle=random.choice(kosten),
            mehraufwand=random.choice([False, False, True]),
            bemerkung=fake.sentence(nb_words=8),
            patient=p,
        )
        db.session.add(a)

    try:
        db.session.commit()
        print(f"✅ Seeding abgeschlossen: {n_addresses} Adressen, {n_patients} Patienten + Aufträge")
    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ Commit-Fehler (evtl. doppelte Auftragsnummer ohne Reset?): {e}")

# seed.py
import random
from datetime import date, time, timedelta
from faker import Faker
from sqlalchemy.exc import IntegrityError
from models import (
    db,
    Patient,
    Adresse,
    Auftrag,
    GeschlechtEnum,
    KostenstelleEnum,
    Angehoeriger,
    Bestattungsinstitut,
    Behoerde
)

def seed_faker(n_addresses=10, n_patients=20, deterministic=True, reset=False):
    """
    Erzeugt Beispiel-Daten:
      - Adressen
      - Patienten (mit Meldeadresse)
      - 1:1 Auftrag pro Patient (inkl. Auftragsadresse)
      - 0..3 Angehörige pro Patient (mit Adresslogik)
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
            ort=fake.city(),
            # distanz=random.randint(1, 60),
        )
        db.session.add(a)
        adressen.append(a)
    
    # einige Institute vorerzeugen
    institute = []
    for i in range(max(1, n_addresses // 5)):  # grob 20% der Adressanzahl
        bi_addr = random.choice(adressen)
        bi = Bestattungsinstitut(
            kurzbezeichnung=f"BI{i+1}",
            firmenname=fake.company(),
            email=fake.company_email(),
            bemerkung=fake.sentence(nb_words=6),
            adresse=bi_addr,
        )
        db.session.add(bi)
        institute.append(bi)
    
    behoerden_pool = []
    for i in range(max(2, n_addresses // 4)):  # grob 25% von n_addresses
        beh_addr = random.choice(adressen)
        b = Behoerde(
            name=f"Standesamt {fake.city()} {i+1}",
            email=(fake.email() if random.random() < 0.7 else None),
            bemerkung=(fake.sentence(nb_words=6) if random.random() < 0.3 else None),
            adresse=beh_addr,
        )
        db.session.add(b)
        behoerden_pool.append(b)

    db.session.flush()  # IDs verfügbar machen

    genders = list(GeschlechtEnum)
    kosten = list(KostenstelleEnum)

    # einfache Liste typischer Verwandtschaftsgrade
    verwandtschaftsgrade = [
        "Ehepartner", "Ehefrau", "Ehemann", "Lebenspartner",
        "Mutter", "Vater", "Tochter", "Sohn",
        "Schwester", "Bruder",
        "Tante", "Onkel", "Nichte", "Neffe",
        "Cousin", "Cousine",
        "Freund", "Freundin",
        "Betreuer", "Nachbar",
    ]

    # 2) Patienten + Auftrag + Angehörige
    for _ in range(n_patients):
        # --- Meldeadresse wählen
        adr_melde = random.choice(adressen)

        # --- Patient
        p = Patient(
            name=fake.last_name(),
            geburtsname=(fake.last_name() if random.random() < 0.25 else None),
            vorname=fake.first_name(),
            geburtsdatum=fake.date_between(start_date="-95y", end_date="-1y"),
            geschlecht=random.choice(genders),
            meldeadresse=adr_melde,
        )
        db.session.add(p)
        db.session.flush()  # p.id verfügbar

        # --- Auftragsadresse bestimmen (50% wie Meldeadresse, sonst andere)
        if random.random() < 0.5:
            adr_auftrag = adr_melde
        else:
            adr_auftrag = random.choice(adressen) if len(adressen) > 1 else adr_melde

        # --- Auftrag
        a = Auftrag(
            auftragsnummer=fake.unique.random_int(min=0, max=9999),
            auftragsdatum=date.today() - timedelta(days=random.randint(0, 30)),
            auftragsuhrzeit=time(hour=random.randint(7, 20),
                                 minute=random.choice([0, 15, 30, 45])),
            kostenstelle=random.choice(kosten),
            mehraufwand=random.choice([False, False, True]),
            bemerkung=fake.sentence(nb_words=8),
            bestattungsinstitut=(
                random.choice(institute) if (institute and random.random() < 0.4) else None
            ),
            patient=p,
            auftragsadresse=adr_auftrag,
        )
        db.session.add(a)
        db.session.flush()

        if behoerden_pool:
            k = min(random.randint(0, 2), len(behoerden_pool))
            # ohne Duplikate
            for b in random.sample(behoerden_pool, k):
                a.behoerden.append(b)

            # gelegentlich zusätzlich eine neue Behörde on-the-fly erzeugen
            if random.random() < 0.1:
                extra_addr = random.choice(adressen)
                b_new = Behoerde(
                    name=f"Ordnungsamt {fake.city()}",
                    email=(fake.email() if random.random() < 0.7 else None),
                    bemerkung=(fake.sentence(nb_words=6) if random.random() < 0.3 else None),
                    adresse=extra_addr,
                )
                db.session.add(b_new); db.session.flush()
                a.behoerden.append(b_new)

        # --- 0..3 Angehörige
        for _ in range(random.randint(0, 3)):
            # Adresse für Angehörigen: Wahrscheinlichkeiten feinjustierbar
            choice = random.choices(
                population=["melde", "auftrag", "neu", "unbekannt"],
                weights=[0.4, 0.25, 0.25, 0.10],
                k=1
            )[0]

            if choice == "melde":
                ang_addr = adr_melde
            elif choice == "auftrag":
                ang_addr = adr_auftrag
            elif choice == "neu":
                # neue Adresse anlegen und in den Pool hängen (damit auch später gewählt werden kann)
                ang_addr = Adresse(
                    strasse=fake.street_name(),
                    hausnummer=fake.building_number(),
                    plz=fake.postcode(),
                    ort=fake.city(),
                )
                db.session.add(ang_addr)
                db.session.flush()
                adressen.append(ang_addr)
            else:  # "unbekannt"
                ang_addr = None

            ang = Angehoeriger(
                name=fake.last_name(),
                vorname=fake.first_name(),
                geschlecht=random.choice(genders),
                verwandtschaftsgrad=random.choice(verwandtschaftsgrade),
                telefonnummer=fake.phone_number(),
                email=fake.email(),
                adresse=ang_addr,
                patient=p,
            )
            db.session.add(ang)

    try:
        db.session.commit()
        print(
            f"✅ Seeding abgeschlossen: {n_addresses} Adressen, "
            f"{n_patients} Patienten + Aufträge + Angehörige + Bestattungsinstitute + Behörden"
        )
    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ Commit-Fehler (evtl. doppelte Auftragsnummer ohne Reset?): {e}")

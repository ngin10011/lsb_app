# lsb_app/seed.py
from datetime import date, time

from lsb_app.extensions import db
from lsb_app.models import (Patient, Adresse, Auftrag,
        Bestattungsinstitut, Verlauf)
from lsb_app.models.enums import (
    GeschlechtEnum,
    KostenstelleEnum,
    AuftragsStatusEnum,
)


def seed_data():
    """Legt einen minimalen, aber gültigen Testdatensatz an."""

    # ---------------------
    # 1) Adresse (Pflichtfelder)
    # ---------------------
    addr = Adresse(
        strasse="Balanstraße",
        hausnummer="63",
        plz="80331",
        ort="München",
    )
    db.session.add(addr)
    db.session.flush()

    # ---------------------
    # 2) Patient (Pflichtfelder)
    # ---------------------
    patient = Patient(
        name="Mustermann",
        vorname="Max",
        geburtsdatum=date(1950, 1, 1),
        geschlecht=GeschlechtEnum.MAENNLICH,
        meldeadresse=addr,
    )
    db.session.add(patient)
    db.session.flush()

    best_addr = Adresse(
        strasse="Damenstiftstraße",
        hausnummer="8",
        plz="80331",
        ort="München",
    )
    db.session.add(best_addr)
    db.session.flush()

    bestattungsinstitut = Bestattungsinstitut(
        kurzbezeichnung='Städtische Bestattung',
        firmenname='Städtische Bestattung München',
        adresse=best_addr,
        email='engincakir19@gmail.com',
    )
    db.session.add(bestattungsinstitut)
    db.session.flush()

    # ---------------------
    # 3) Auftrag (Pflichtfelder)
    # ---------------------
    auftrag = Auftrag(
        auftragsnummer=1000,
        patient=patient,
        auftragsadresse=addr,

        auftragsdatum=date(2025, 11, 29),
        auftragsuhrzeit=time(10, 30),

        kostenstelle=KostenstelleEnum.BESTATTUNGSINSTITUT,
        mehraufwand=False,
        status=AuftragsStatusEnum.READY,   # typischer Startstatus

        bestattungsinstitut=bestattungsinstitut,

        # Optional:
        # bemerkung="Seed-Testauftrag",
        # auftragsnummer=None,
        # bestattungsinstitut_id=None,
    )

    db.session.add(auftrag)
    db.session.flush()

    verlauf = Verlauf(
        datum=date.today(),
        ereignis='TB-Auftrag angelegt',
        auftrag=auftrag,   
    )
    db.session.add(verlauf)

    db.session.commit()

# models.py
from flask_sqlalchemy import SQLAlchemy
from enum import Enum
from sqlalchemy import Enum as SqlEnum

db = SQLAlchemy()

class GeschlechtEnum(str, Enum):
    MAENNLICH = "männlich"
    WEIBLICH = "weiblich"
    DIVERS = "divers"
    UNBEKANNT = "unbekannt"

class KostenstelleEnum(str, Enum):
    ANGEHOERIGE = "Angehörige"
    BESTATTUNGSINSTITUT = "Bestattungsinstitut"
    BEHOERDE = "Behörde"
    UNBEKANNT = "unbekannt"

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    geburtsname = db.Column(db.String(120), nullable=True)
    vorname = db.Column(db.String(120), nullable=False)
    geburtsdatum = db.Column(db.Date, nullable=False)
    geschlecht = db.Column(SqlEnum(GeschlechtEnum), nullable=False)

    meldeadresse_id   = db.Column(db.Integer, db.ForeignKey("adresse.id"), nullable=False)
    meldeadresse      = db.relationship("Adresse", back_populates="patienten")

    auftrag = db.relationship(
        "Auftrag",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,   # sinnvoll in Kombi mit delete-orphan
    )

class Adresse(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    strasse   = db.Column(db.String(120), nullable=False)
    hausnummer= db.Column(db.String(20),  nullable=False)
    plz       = db.Column(db.String(10),  nullable=False)
    ort       = db.Column(db.String(120), nullable=False)
    distanz   = db.Column(db.Integer)

    # 1:n: eine Adresse hat viele Patienten
    patienten = db.relationship(
        "Patient",
        back_populates="meldeadresse",
        lazy="dynamic"  # optional: für filterbare Query (adresse.patienten.filter(...))
    )

    def __repr__(self):
        return f"{self.strasse} {self.hausnummer}, {self.plz} {self.ort}"

class Auftrag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auftragsnummer = db.Column(db.Integer, unique=True)
    auftragsdatum = db.Column(db.Date, nullable=False)
    auftragsuhrzeit = db.Column(db.Time, nullable=False)
    kostenstelle = db.Column(SqlEnum(KostenstelleEnum), nullable=False)
    mehraufwand = db.Column(db.Boolean, nullable=False)
    bemerkung = db.Column(db.Text, nullable=True)

    # 1:1 zu Patient 
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # macht die Beziehung 1:1
        index=True,
    )
    patient = db.relationship("Patient", back_populates="auftrag")

    # 1:n Adresse -> Auftrag
    auftragsadresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"), nullable=False)
    auftragsadresse = db.relationship("Adresse")
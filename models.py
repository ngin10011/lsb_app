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

class AuftragsStatusEnum(str, Enum):
    READY = "READY"
    WAIT  = "WAIT"
    TODO  = "TODO"
    SENT  = "SENT"
    DONE  = "DONE"

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

    angehoerige = db.relationship(
        "Angehoeriger",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
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

auftrag_behoerde = db.Table(
    "auftrag_behoerde",
    db.Column("auftrag_id", db.Integer, db.ForeignKey("auftrag.id", ondelete="CASCADE"), primary_key=True),
    db.Column("behoerde_id", db.Integer, db.ForeignKey("behoerde.id", ondelete="CASCADE"), primary_key=True),
)

class Auftrag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auftragsnummer = db.Column(db.Integer, unique=True)
    auftragsdatum = db.Column(db.Date, nullable=False)
    auftragsuhrzeit = db.Column(db.Time, nullable=False)
    kostenstelle = db.Column(SqlEnum(KostenstelleEnum), nullable=False)
    mehraufwand = db.Column(db.Boolean, nullable=False)
    status = db.Column(SqlEnum(AuftragsStatusEnum), nullable=False, index=True)
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

    bestattungsinstitut_id = db.Column(
        db.Integer,
        db.ForeignKey("bestattungsinstitut.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    bestattungsinstitut = db.relationship("Bestattungsinstitut", back_populates="auftraege")

    behoerden = db.relationship(
        "Behoerde",
        secondary=auftrag_behoerde,
        lazy="selectin",
        backref=db.backref("auftraege", lazy="selectin"),
        cascade="save-update",
    )

class Angehoeriger(db.Model):
    __tablename__ = "angehoeriger"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    vorname = db.Column(db.String(120))
    geschlecht = db.Column(SqlEnum(GeschlechtEnum))
    verwandtschaftsgrad = db.Column(db.String(80))
    telefonnummer = db.Column(db.String(50))
    email = db.Column(db.String(120))

    # Adresse optional (unbekannt erlaubt)
    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"))
    adresse = db.relationship("Adresse")

    # 1:n zu Patient
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True)
    patient = db.relationship("Patient", back_populates="angehoerige")

    def __repr__(self):
        return f"{self.name}, {self.vorname}, {self.telefonnummer} {self.email}"
    
class Bestattungsinstitut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kurzbezeichnung = db.Column(db.String(80), nullable=False, unique=True)
    firmenname = db.Column(db.String(200), nullable=False)

    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"))
    adresse = db.relationship("Adresse")

    email = db.Column(db.String(120))
    anschreibbar = db.Column(db.Boolean, default=True)
    bemerkung = db.Column(db.Text)

    # Beziehung zu Auftrag: 1:n
    auftraege = db.relationship(
        "Auftrag",
        back_populates="bestattungsinstitut",
        cascade="all, delete",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"{self.kurzbezeichnung} ({self.firmenname})"


class Behoerde(db.Model):
    __tablename__ = "behoerde"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    bemerkung = db.Column(db.Text)

    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"), nullable=False)
    adresse = db.relationship("Adresse")

    def __repr__(self):
        return f"{self.name} ({self.adresse})"
    

# lsb_app/models/patient.py
from sqlalchemy import Enum as SAEnum, Index
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin
from lsb_app.models.enums import GeschlechtEnum

class Patient(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "patient"

    name         = db.Column(db.String(120), nullable=False)
    geburtsname  = db.Column(db.String(120), nullable=True)
    vorname      = db.Column(db.String(120), nullable=False)
    geburtsdatum = db.Column(db.Date, nullable=False)

    geschlecht = db.Column(
        SAEnum(GeschlechtEnum, native_enum=False, validate_strings=True),
        nullable=False
    )

    meldeadresse_id = db.Column(
        db.Integer,
        db.ForeignKey("adresse.id", ondelete="RESTRICT"),
        nullable=False
    )
    meldeadresse = db.relationship(
        "Adresse",
        back_populates="patienten",
        lazy="selectin",
    )

    # 1:1 Auftrag
    auftrag = db.relationship(
        "Auftrag",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )

    # 1:n Angehörige
    angehoerige = db.relationship(
        "Angehoeriger",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_patient_name_vorname", "name", "vorname"),
        Index("ix_patient_geburtsdatum", "geburtsdatum"),
    )

    def __repr__(self) -> str:
        return f"<Patient #{self.id} {self.name}, {self.vorname}>"

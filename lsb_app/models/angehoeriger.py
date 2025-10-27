# lsb_app/models/angehoeriger.py
from sqlalchemy import Enum as SAEnum
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin
from lsb_app.models.enums import GeschlechtEnum

class Angehoeriger(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "angehoeriger"

    name = db.Column(db.String(120))
    vorname = db.Column(db.String(120))
    geschlecht = db.Column(SAEnum(GeschlechtEnum, native_enum=False, validate_strings=True))
    verwandtschaftsgrad = db.Column(db.String(80))
    telefonnummer = db.Column(db.String(50))
    email = db.Column(db.String(120))

    # optionale Adresse
    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"))
    adresse = db.relationship("Adresse")

    # 1:n zu Patient
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    patient = db.relationship("Patient", back_populates="angehoerige")

    def __repr__(self) -> str:
        return f"{self.name}, {self.vorname}, {self.telefonnummer} {self.email}"

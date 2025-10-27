# lsb_app/models/adresse.py
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin

class Adresse(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "adresse"

    strasse    = db.Column(db.String(120), nullable=False)
    hausnummer = db.Column(db.String(20), nullable=False)
    plz       = db.Column(db.String(10), nullable=False)
    ort       = db.Column(db.String(120), nullable=False)
    distanz   = db.Column(db.Integer)

    # 1:n: eine Adresse hat viele Patienten (Meldeadresse)
    patienten = db.relationship(
        "Patient",
        back_populates="meldeadresse",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"{self.strasse} {self.hausnummer}, {self.plz} {self.ort}"

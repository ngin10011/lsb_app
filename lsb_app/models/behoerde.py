# lsb_app/models/behoerde.py
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin

class Behoerde(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "behoerde"

    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    bemerkung = db.Column(db.Text)

    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"), nullable=False)
    adresse = db.relationship("Adresse")

    # m:n zu Auftrag über Assoziationstabelle
    auftraege = db.relationship(
        "Auftrag",
        secondary="auftrag_behoerde",
        back_populates="behoerden",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"{self.name} ({self.adresse})"

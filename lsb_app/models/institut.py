# lsb_app/models/institut.py
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin

class Bestattungsinstitut(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "bestattungsinstitut"

    kurzbezeichnung = db.Column(db.String(80), nullable=False, unique=True)
    firmenname = db.Column(db.String(200), nullable=False)

    adresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"))
    adresse = db.relationship("Adresse")

    email = db.Column(db.String(120))
    anschreibbar = db.Column(db.Boolean, default=True)
    bemerkung = db.Column(db.Text)

    # 1:n zu Auftrag
    auftraege = db.relationship(
        "Auftrag",
        back_populates="bestattungsinstitut",
        cascade="all, delete",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"{self.kurzbezeichnung} ({self.firmenname})"

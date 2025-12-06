# lsb_app/models/auftrag.py
from sqlalchemy import Enum as SAEnum
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin
from lsb_app.models.enums import KostenstelleEnum, AuftragsStatusEnum
from lsb_app.models.associations import auftrag_behoerde

class Auftrag(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "auftrag"

    auftragsnummer  = db.Column(db.Integer, unique=True)
    auftragsdatum   = db.Column(db.Date, nullable=False)
    auftragsuhrzeit = db.Column(db.Time, nullable=False)
    kostenstelle    = db.Column(SAEnum(KostenstelleEnum, native_enum=False, validate_strings=True), nullable=False)
    mehraufwand     = db.Column(db.Boolean, nullable=False)
    status          = db.Column(SAEnum(AuftragsStatusEnum, native_enum=False, validate_strings=True), nullable=False, index=True)
    bemerkung       = db.Column(db.Text, nullable=True)

    wait_due_date = db.Column(db.Date, nullable=True)

    # 1:1 zu Patient
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    patient = db.relationship("Patient", back_populates="auftrag")

    # 1:n Adresse -> Auftrag
    auftragsadresse_id = db.Column(db.Integer, db.ForeignKey("adresse.id"), nullable=False)
    auftragsadresse = db.relationship("Adresse")

    # optionales Bestattungsinstitut (1:n)
    bestattungsinstitut_id = db.Column(
        db.Integer,
        db.ForeignKey("bestattungsinstitut.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bestattungsinstitut = db.relationship("Bestattungsinstitut", back_populates="auftraege")

    # m:n Behörden
    behoerden = db.relationship(
        "Behoerde",
        secondary=auftrag_behoerde,
        back_populates="auftraege",
        lazy="selectin",
        cascade="save-update",
    )

    # 1:n
    rechnungen = db.relationship(
        "Rechnung",
        back_populates="auftrag",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # 1:n
    verlaeufe = db.relationship(
        "Verlauf",
        back_populates="auftrag",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Auftrag #{self.id} Patient={self.patient_id}>"

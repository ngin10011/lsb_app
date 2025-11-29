# lsb_app/models/rechnung.py
from sqlalchemy import Enum as SAEnum, Index
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin
from lsb_app.models.enums import RechnungsArtEnum, RechnungsStatusEnum

class Rechnung(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "rechnung"

    version = db.Column(db.Integer, nullable=False)
    art = db.Column(
        SAEnum(RechnungsArtEnum, native_enum=False, validate_strings=True),
        nullable=False
    )
    rechnungsdatum   = db.Column(db.Date, nullable=False)
    bemerkung = db.Column(db.Text)
    betrag = db.Column(db.Numeric(12, 2), nullable=False)

    status = db.Column(
        SAEnum(RechnungsStatusEnum, native_enum=False, validate_strings=True),
        nullable=False,
        default=RechnungsStatusEnum.CREATED,
        server_default=RechnungsStatusEnum.CREATED.value,
    )

    pdf_path = db.Column(db.String(512), nullable=True, index=True)

    # 1:n Auftrag
    auftrag_id = db.Column(
        db.Integer,
        db.ForeignKey("auftrag.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    auftrag = db.relationship("Auftrag", back_populates="rechnungen", lazy="selectin")

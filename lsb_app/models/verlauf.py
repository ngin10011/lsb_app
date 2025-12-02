# lsb_app/models/verlauf.py
from sqlalchemy import Enum as SAEnum, Index
from lsb_app.extensions import db
from lsb_app.models.base import IDMixin, TimestampMixin

class Verlauf(IDMixin, TimestampMixin, db.Model):
    __tablename__ = "verlauf"

    datum   = db.Column(db.Date, nullable=False)
    ereignis = db.Column(db.Text, nullable=False)

    # 1:n Auftrag
    auftrag_id = db.Column(
        db.Integer,
        db.ForeignKey("auftrag.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    auftrag = db.relationship("Auftrag", back_populates="verlaeufe", lazy="selectin")

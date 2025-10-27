# lsb_app/models/associations.py
from lsb_app.extensions import db

auftrag_behoerde = db.Table(
    "auftrag_behoerde",
    db.Column("auftrag_id", db.Integer, db.ForeignKey("auftrag.id", ondelete="CASCADE"), primary_key=True),
    db.Column("behoerde_id", db.Integer, db.ForeignKey("behoerde.id", ondelete="CASCADE"), primary_key=True),
)

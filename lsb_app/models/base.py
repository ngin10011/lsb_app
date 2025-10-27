# lsb_app/models/base.py
from sqlalchemy.sql import func
from lsb_app.extensions import db

class IDMixin:
    id = db.Column(db.Integer, primary_key=True)

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

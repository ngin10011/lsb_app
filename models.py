# models.py
from flask_sqlalchemy import SQLAlchemy
from enum import Enum
from sqlalchemy import Enum as SqlEnum

db = SQLAlchemy()

class GeschlechtEnum(str, Enum):
    MAENNLICH = "männlich"
    WEIBLICH = "weiblich"
    DIVERS = "divers"
    UNBEKANNT = "unbekannt"

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    geburtsname = db.Column(db.String(120), nullable=True)
    vorname = db.Column(db.String(120), nullable=False)
    geburtsdatum = db.Column(db.Date, nullable=False)
    geschlecht = db.Column(SqlEnum(GeschlechtEnum), nullable=False)

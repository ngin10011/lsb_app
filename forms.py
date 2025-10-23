# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, TimeField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from enum import Enum

class GeschlechtEnum(Enum):
    MAENNLICH = "männlich"
    WEIBLICH = "weiblich"
    DIVERS = "divers"
    UNBEKANNT = "unbekannt"

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

class PatientForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsname = StringField("Geburtsname", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    vorname = StringField("Vorname", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsdatum = DateField("Geburtsdatum", validators=[DataRequired()], format="%Y-%m-%d")
    geschlecht = SelectField(
        "Geschlecht",
        choices=[
            ("männlich", "männlich"),
            ("weiblich", "weiblich"),
            ("divers", "divers"),
            ("unbekannt", "unbekannt"),
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Erster Eintrag leer (Platzhalter), danach alle Enum-Werte
        self.geschlecht.choices = [("", "— bitte wählen —")] + [
            (g, g.value) for g in GeschlechtEnum
        ]
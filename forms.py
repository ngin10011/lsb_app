# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from models import GeschlechtEnum  # ✅ importiere das Enum von dort

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

def coerce_geschlecht(v):
    # akzeptiere None/""/ "None" als leer
    if v in (None, "", "None"):
        return None
    if isinstance(v, GeschlechtEnum):
        return v
    return GeschlechtEnum(v)  # mappt Strings wie "männlich" -> Enum

class PatientForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsname = StringField("Geburtsname", validators=[Length(max=120)], filters=[strip_or_none])
    vorname = StringField("Vorname", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsdatum = DateField("Geburtsdatum", validators=[DataRequired()], format="%Y-%m-%d")
    geschlecht = SelectField("Geschlecht", choices=[], validators=[DataRequired()], coerce=coerce_geschlecht)
    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geschlecht.choices = [("", "— bitte wählen —")] + [
            (g.value, g.value) for g in GeschlechtEnum
        ]

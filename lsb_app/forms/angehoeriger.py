# lsb_app/forms/angehoeriger.py
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, Optional, Email
from lsb_app.models import GeschlechtEnum

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

def coerce_geschlecht(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, GeschlechtEnum):
        return v
    # Werte sind Strings wie "männlich" -> Enum via value
    return GeschlechtEnum(v)

class AngehoerigerForm(FlaskForm):
    name   = StringField("Name (Angehöriger)", validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    vorname= StringField("Vorname (Angehöriger)", validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    geschlecht = SelectField("Geschlecht", choices=[], validators=[Optional()], coerce=coerce_geschlecht)
    verwandtschaftsgrad = StringField("Verwandtschaftsgrad", validators=[Optional(), Length(max=80)], filters=[strip_or_none])
    telefonnummer = StringField("Telefonnummer", validators=[Optional(), Length(max=50)], filters=[strip_or_none])
    email = EmailField("E-Mail", validators=[Optional(), Email(), Length(max=120)], filters=[strip_or_none])
    adresse_id = SelectField("Adresse", coerce=int,
                             validators=[DataRequired(message="Bitte eine Adresse auswählen.")])
    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geschlecht.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in GeschlechtEnum]

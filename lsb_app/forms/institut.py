from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Email, InputRequired
from lsb_app.models import RechnungsadressModus

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

def coerce_modus(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, RechnungsadressModus):
        return v
    # Werte sind Strings wie "männlich" -> Enum via value
    return RechnungsadressModus(v)

class InstitutForm(FlaskForm):
    kurzbezeichnung = StringField(
        "Kurzbezeichnung",
        validators=[DataRequired(), Length(max=120)],
        filters=[strip_or_none],
    )
    firmenname = StringField(
        "Firmenname",
        validators=[DataRequired(), Length(max=200)],
        filters=[strip_or_none],
    )
    email = StringField(
        "E-Mail",
        validators=[Optional(), Email(), Length(max=200)],
        filters=[strip_or_none],
    )
    bemerkung = TextAreaField(
        "Bemerkung",
        validators=[Optional(), Length(max=2000)],
        filters=[strip_or_none],
    )
    anschreibbar = BooleanField("Anschreibbar")
    adresse_id = SelectField("Adresse", coerce=int, 
                             validators=[InputRequired(message="Bitte eine Adresse auswählen.")])
    
    rechnungadress_modus = SelectField("Modus", choices=[], validators=[DataRequired()], coerce=coerce_modus)

    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rechnungadress_modus.choices = [(g.value, g.value) for g in RechnungsadressModus]


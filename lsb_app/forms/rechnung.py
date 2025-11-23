# lsb_app/forms/rechnung.py
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional
from lsb_app.models import RechnungsArtEnum
from datetime import date

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

def coerce_rechnungsart(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, RechnungsArtEnum):
        return v
    # Werte sind Strings wie "männlich" -> Enum via value
    return RechnungsArtEnum(v)

class RechnungForm(FlaskForm):
    art = SelectField("Art", choices=[], validators=[DataRequired()], coerce=coerce_rechnungsart)
    rechnungsdatum = DateField(
        "Rechnungsdatum", 
        validators=[DataRequired()], 
        format="%Y-%m-%d",
        default=date.today)
    bemerkung = TextAreaField(
        "Bemerkung",
        validators=[Optional(), Length(max=2000)],
        filters=[strip_or_none],
    )

    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.art.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in RechnungsArtEnum]

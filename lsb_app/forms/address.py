# lsb_app/forms/address.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

class AddressForm(FlaskForm):
    strasse    = StringField("Straße",     validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    hausnummer = StringField("Nr.",        validators=[DataRequired(), Length(max=20)],  filters=[strip_or_none])
    plz        = StringField("PLZ",        validators=[DataRequired(), Length(max=10)],  filters=[strip_or_none])
    ort        = StringField("Ort",        validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    distanz    = IntegerField("Distanz",   validators=[DataRequired()])
    submit     = SubmitField("Speichern")

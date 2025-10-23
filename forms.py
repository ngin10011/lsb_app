from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, TimeField, FloatField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

class PatientForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    vorname = StringField("Vorname", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsdatum = DateField("Geburtsdatum", validators=[DataRequired()], format="%Y-%m-%d")
    gewicht = FloatField("Gewicht (kg)", validators=[DataRequired(), NumberRange(min=0)])
    bemerkung = TextAreaField("Bemerkung", validators=[Optional()], filters=[strip_or_none])
    submit = SubmitField("Speichern")
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Email, InputRequired

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

class BehoerdeForm(FlaskForm):
    name = StringField(
        "Name",
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

    adresse_id = SelectField("Adresse", coerce=int, 
                             validators=[InputRequired(message="Bitte eine Adresse auswählen.")])
    submit = SubmitField("Speichern")

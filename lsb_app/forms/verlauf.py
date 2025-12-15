# lsb_app/forms/verlauf.py
from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class VerlaufForm(FlaskForm):
    datum = DateField("Datum", validators=[DataRequired()])
    ereignis = TextAreaField(
        "Ereignis",
        validators=[DataRequired(), Length(min=2, max=10_000)],
        render_kw={"rows": 6},
    )
    submit = SubmitField("Speichern")

class DeleteForm(FlaskForm):
    submit = SubmitField("Löschen")
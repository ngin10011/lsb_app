# lsb_app/forms/zahlung.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, DateField
from wtforms.validators import DataRequired, NumberRange
from decimal import Decimal
from datetime import date


class ZahlungEingangForm(FlaskForm):
    payee = StringField("Name", validators=[DataRequired()])

    betrag = DecimalField(
        "Betrag (€)",
        places=2,
        validators=[DataRequired(), NumberRange(min=Decimal("0.00"))],
    )

    auftragsnummer = StringField("Auftragsnummer", validators=[DataRequired()])

    eingangsdatum = DateField(
        "Datum",
        validators=[DataRequired()],
        # default=date.today,   # heute vorbelegen
    )

    submit = SubmitField("Speichern")

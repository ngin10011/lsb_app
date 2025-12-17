# lsb_app/forms/auftrag.py
from flask_wtf import FlaskForm
from wtforms import IntegerField, DateField, TimeField, SelectField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import Optional, NumberRange, Length, DataRequired, ValidationError
from lsb_app.models import KostenstelleEnum, AuftragsStatusEnum

def coerce_enum(enum_cls):
    def _coerce(v):
        if v in (None, "", "None"):
            return None
        if isinstance(v, enum_cls):
            return v
        return enum_cls(v)
    return _coerce

class AuftragForm(FlaskForm):
    auftragsnummer  = IntegerField("Auftragsnummer", validators=[Optional(), NumberRange(min=1)])
    auftragsdatum   = DateField("Datum", validators=[Optional()], format="%Y-%m-%d")
    auftragsuhrzeit = TimeField("Uhrzeit", validators=[Optional()], format="%H:%M")
    kostenstelle    = SelectField("Kostenstelle", validators=[Optional()], coerce=coerce_enum(KostenstelleEnum))
    status          = SelectField("Status", validators=[Optional()], coerce=coerce_enum(AuftragsStatusEnum))
    mehraufwand     = BooleanField("Mehraufwand", default=False)
    bemerkung       = TextAreaField("Bemerkung", validators=[Optional(), Length(max=2000)])
    auftragsadresse_id = SelectField("Adresse", coerce=int,
                            validators=[DataRequired(message="Bitte eine Adresse auswählen.")])
    wait_due_date = DateField("warten bis", validators=[Optional()], format="%Y-%m-%d")
    submit          = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kostenstelle.choices = [("", "— bitte wählen —")] + [(k.value, k.value) for k in KostenstelleEnum]
        self.status.choices       = [("", "— bitte wählen —")] + [(s.value, s.value) for s in AuftragsStatusEnum]

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators=extra_validators)
        if not ok:
            return False

        if self.status.data == AuftragsStatusEnum.WAIT and not self.wait_due_date.data:
            self.wait_due_date.errors.append(
                "Bitte ein Fälligkeitsdatum angeben, wenn der Status WAIT ist."
            )
            return False

        return True
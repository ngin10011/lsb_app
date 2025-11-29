# lsb_app/forms/rechnung.py
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional
from lsb_app.models import RechnungsArtEnum, RechnungsStatusEnum
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

def coerce_rechnungsstatus(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, RechnungsStatusEnum):
        return v
    # Werte sind Strings wie "männlich" -> Enum via value
    return RechnungsStatusEnum(v)

class RechnungForm(FlaskForm):
    art = SelectField("Art", choices=[], validators=[DataRequired()], coerce=coerce_rechnungsart)
    status = SelectField("Status", choices=[], validators=[DataRequired()], coerce=coerce_rechnungsstatus)
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
    submit_generate = SubmitField("Rechnung erstellen")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.art.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in RechnungsArtEnum]
        self.status.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in RechnungsStatusEnum]

class RechnungBaseForm(FlaskForm):
    art = SelectField(
        "Art",
        choices=[],
        validators=[DataRequired()],
        coerce=coerce_rechnungsart,
    )
    rechnungsdatum = DateField(
        "Rechnungsdatum",
        validators=[DataRequired()],
        format="%Y-%m-%d",
        default=date.today,
    )
    bemerkung = TextAreaField(
        "Bemerkung",
        validators=[Optional(), Length(max=2000)],
        filters=[strip_or_none],
    )

    # Für create.html
    submit_generate = SubmitField("Rechnung erstellen")
    # Für edit.html könntest du noch ein submit_edit definieren, wenn du willst

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.art.choices = [("", "— bitte wählen —")] + [
            (g.value, g.value) for g in RechnungsArtEnum
        ]


class RechnungCreateForm(RechnungBaseForm):
    """Form nur für das Anlegen einer Rechnung (kein Status-Feld)."""
    pass


class RechnungEditForm(RechnungBaseForm):
    """Form für das Bearbeiten einer bestehenden Rechnung (mit Status)."""

    status = SelectField(
        "Status",
        choices=[],
        validators=[DataRequired()],
        coerce=coerce_rechnungsstatus,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [("", "— bitte wählen —")] + [
            (g.value, g.value) for g in RechnungsStatusEnum
        ]
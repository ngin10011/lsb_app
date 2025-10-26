# forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, DateField, SelectField, SubmitField, TimeField,
                     IntegerField, BooleanField, TextAreaField, FieldList, FormField)
try:
    from wtforms import EmailField
except ImportError:
    from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from models import GeschlechtEnum, KostenstelleEnum

def strip_or_none(v):
    return v.strip() if isinstance(v, str) and v.strip() != "" else None

def coerce_geschlecht(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, GeschlechtEnum):
        return v
    return GeschlechtEnum(v)

def coerce_kostenstelle(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, KostenstelleEnum):
        return v
    return KostenstelleEnum(v)

class AngehoerigerMiniForm(FlaskForm):
    name   = StringField("Name (Angehöriger)", validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    vorname= StringField("Vorname (Angehöriger)", validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    geschlecht = SelectField("Geschlecht", choices=[], validators=[Optional()], coerce=coerce_geschlecht)
    verwandtschaftsgrad = StringField("Verwandtschaftsgrad", validators=[Optional(), Length(max=80)], filters=[strip_or_none])
    telefonnummer = StringField("Telefonnummer", validators=[Optional(), Length(max=50)], filters=[strip_or_none])
    email = EmailField("E-Mail", validators=[Optional(), Email(), Length(max=120)], filters=[strip_or_none])

    adresse_choice = SelectField("Adresse", coerce=int, validators=[Optional()])
    # neue Adresse (nur falls adresse_choice == -1)
    strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

class PatientForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsname = StringField("Geburtsname", validators=[Length(max=120)], filters=[strip_or_none])
    vorname = StringField("Vorname", validators=[DataRequired(), Length(max=120)], filters=[strip_or_none])
    geburtsdatum = DateField("Geburtsdatum", validators=[DataRequired()], format="%Y-%m-%d")
    geschlecht = SelectField("Geschlecht", choices=[], validators=[DataRequired()], coerce=coerce_geschlecht)
    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geschlecht.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in GeschlechtEnum]

class TBPatientForm(PatientForm):
    # Meldeadresse (Select-or-Create)
    meldeadresse_id = SelectField("Meldeadresse", coerce=int, validators=[Optional()])
    new_strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    new_hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    new_plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    new_ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

    # Auftrag
    auftragsnummer  = IntegerField("Auftragsnummer", validators=[DataRequired(), NumberRange(min=1)])
    auftragsdatum   = DateField("Auftragsdatum",     validators=[DataRequired()], format="%Y-%m-%d")
    auftragsuhrzeit = TimeField("Auftragsuhrzeit",   validators=[DataRequired()], format="%H:%M")
    kostenstelle    = SelectField("Kostenstelle",    validators=[DataRequired()], coerce=coerce_kostenstelle)
    mehraufwand     = BooleanField("Mehraufwand", default=False)
    bemerkung       = TextAreaField("Bemerkung", validators=[Optional(), Length(max=2000)])

    # Auftragsadresse (Select-or-Create)
    auftragsadresse_id = SelectField("Auftragsadresse", coerce=int, validators=[Optional()])
    auftrag_strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    auftrag_hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    auftrag_plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    auftrag_ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

    # 🔹 Mehrere Angehörige
    angehoerige = FieldList(FormField(AngehoerigerMiniForm), min_entries=1, max_entries=10)

    # Buttons
    add_relative = SubmitField("Weiteren Angehörigen hinzufügen")
    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kostenstelle.choices = [("", "— bitte wählen —")] + [(k.value, k.value) for k in KostenstelleEnum]
        # Unterform-Choices pro Eintrag setzen
        for sub in self.angehoerige:
            sub.form.geschlecht.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in GeschlechtEnum]
            # -2: wie Melde, -4: wie Auftrag, -1: Neu, -3: Unbekannt
            sub.form.adresse_choice.choices = [
                (-2, "🟰 Wie Meldeadresse"),
                (-4, "🟰 Wie Auftragsadresse"),
                (-1, "➕ Neue Adresse anlegen…"),
                (-3, "Unbekannt"),
            ]

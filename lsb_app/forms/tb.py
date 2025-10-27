# lsb_app/forms/tb.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, DateField, SelectField, SubmitField, TimeField,
    IntegerField, BooleanField, TextAreaField, FieldList, FormField
)
try:
    from wtforms import EmailField
except ImportError:
    from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email, ValidationError

from .patient import PatientForm  # TBPatientForm erbt davon
from lsb_app.models import GeschlechtEnum, KostenstelleEnum, AuftragsStatusEnum

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

def coerce_status(v):
    if v in (None, "", "None"):
        return None
    if isinstance(v, AuftragsStatusEnum):
        return v
    return AuftragsStatusEnum(v)

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

class BehoerdeMiniForm(FlaskForm):
    sel_behoerde_id = SelectField("Behörde", coerce=int, validators=[Optional()])

    name = StringField("Name", validators=[Optional(), Length(max=200)], filters=[strip_or_none])
    email = EmailField("E-Mail", validators=[Optional(), Email(), Length(max=120)], filters=[strip_or_none])
    bemerkung = TextAreaField("Bemerkung", validators=[Optional(), Length(max=2000)])

    beh_adresse_id = SelectField("Adressauswahl", coerce=int, validators=[Optional()])
    beh_strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    beh_hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    beh_plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    beh_ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

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
    status          = SelectField("Status", validators=[DataRequired()], coerce=coerce_status)
    bemerkung       = TextAreaField("Bemerkung", validators=[Optional(), Length(max=2000)])

    # Auftragsadresse (Select-or-Create)
    auftragsadresse_id = SelectField("Auftragsadresse", coerce=int, validators=[Optional()])
    auftrag_strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    auftrag_hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    auftrag_plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    auftrag_ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

    # Angehörige
    angehoerige = FieldList(FormField(AngehoerigerMiniForm), min_entries=1, max_entries=10)
    add_relative = SubmitField("Weiteren Angehörigen hinzufügen")

    # Bestattungsinstitut (Select-or-Create)
    bestattungsinstitut_id = SelectField("Bestattungsinstitut", coerce=int, validators=[Optional()])
    bi_kurz = StringField("Kurzbezeichnung", validators=[Optional(), Length(max=80)],  filters=[strip_or_none])
    bi_firma = StringField("Firmenname",     validators=[Optional(), Length(max=200)], filters=[strip_or_none])
    bi_email = EmailField("E-Mail",          validators=[Optional(), Email(), Length(max=120)], filters=[strip_or_none])
    bi_bemerkung = TextAreaField("Bemerkung", validators=[Optional(), Length(max=2000)])
    bi_adresse_id = SelectField("Adresse des Instituts", coerce=int, validators=[Optional()])
    bi_strasse    = StringField("Straße",     validators=[Optional(), Length(max=120)], filters=[strip_or_none])
    bi_hausnummer = StringField("Nr.",        validators=[Optional(), Length(max=20)],  filters=[strip_or_none])
    bi_plz        = StringField("PLZ",        validators=[Optional(), Length(max=10)],  filters=[strip_or_none])
    bi_ort        = StringField("Ort",        validators=[Optional(), Length(max=120)], filters=[strip_or_none])

    # Behörden
    behoerden = FieldList(FormField(BehoerdeMiniForm), min_entries=1, max_entries=10)
    add_behoerde = SubmitField("Weitere Behörde hinzufügen")

    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kostenstelle.choices = [("", "— bitte wählen —")] + [(k.value, k.value) for k in KostenstelleEnum]
        self.status.choices = [("", "— bitte wählen —")] + [(s.value, s.value) for s in AuftragsStatusEnum]
        for sub in self.angehoerige:
            sub.form.geschlecht.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in GeschlechtEnum]
            sub.form.adresse_choice.choices = [
                (0,  "— bitte wählen —"),
                (-2, "🟰 Wie Meldeadresse"),
                (-4, "🟰 Wie Auftragsadresse"),
                (-1, "➕ Neue Adresse anlegen…"),
                (-3, "Unbekannt"),
            ]
            if sub.form.adresse_choice.data is None:
                sub.form.adresse_choice.data = 0

    def validate_auftragsnummer(self, field):
        if field.data is None:
            return
        from lsb_app.models import Auftrag  # lokaler Import vermeidet Zyklus
        exists = Auftrag.query.filter_by(auftragsnummer=field.data).first()
        if exists:
            raise ValidationError("Auftragsnummer bereits vergeben.")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)

        ks = self.kostenstelle.data  # Enum: KostenstelleEnum

        # Fall A: Kostenstelle = Bestattungsinstitut
        if ks == KostenstelleEnum.BESTATTUNGSINSTITUT:
            bi_sel = self.bestattungsinstitut_id.data  # 0 = kein, >0 = bestehend, -1 = neu
            if bi_sel in (None, 0):
                self.bestattungsinstitut_id.errors.append(
                    "Bitte ein Bestattungsinstitut auswählen oder neu anlegen."
                )
                ok = False
            elif bi_sel == -1:
                if not self.bi_kurz.data:
                    self.bi_kurz.errors.append("Erforderlich bei Neuanlage.")
                    ok = False
                if not self.bi_firma.data:
                    self.bi_firma.errors.append("Erforderlich bei Neuanlage.")
                    ok = False
                if self.bi_adresse_id.data == -1:
                    for f in (self.bi_strasse, self.bi_hausnummer, self.bi_plz, self.bi_ort):
                        if not f.data:
                            f.errors.append("Erforderlich.")
                            ok = False

        # Fall B: Kostenstelle = Behörde
        if ks == KostenstelleEnum.BEHOERDE:
            any_selected = False
            for sub in self.behoerden.entries:
                f = sub.form
                sel = f.sel_behoerde_id.data  # 0 = keine, >0 = bestehend, -1 = neu

                if sel and sel > 0:
                    any_selected = True
                    break

                if sel == -1:
                    if not f.name.data:
                        f.name.errors.append("Name der Behörde erforderlich.")
                        ok = False
                    if f.beh_adresse_id.data == -1:
                        for fld in (f.beh_strasse, f.beh_hausnummer, f.beh_plz, f.beh_ort):
                            if not fld.data:
                                fld.errors.append("Erforderlich.")
                                ok = False
                    any_selected = True

            if not any_selected:
                if self.behoerden.entries:
                    self.behoerden.entries[0].form.sel_behoerde_id.errors.append(
                        "Bitte mindestens eine Behörde auswählen oder neu anlegen."
                    )
                ok = False

        # Angehörige: allgemeine Prüfung
        for sub in self.angehoerige.entries:
            f = sub.form
            any_person_field = any([
                f.name.data, f.vorname.data, f.verwandtschaftsgrad.data,
                f.telefonnummer.data, f.email.data
            ])
            if not any_person_field:
                continue
            if f.adresse_choice.data in (None, 0):
                f.adresse_choice.errors.append("Bitte eine Adresse auswählen.")
                ok = False
            if f.adresse_choice.data == -1:
                for fld in (f.strasse, f.hausnummer, f.plz, f.ort):
                    if not fld.data:
                        fld.errors.append("Erforderlich.")
                        ok = False

        # Fall C: Kostenstelle = Angehörige
        if ks == KostenstelleEnum.ANGEHOERIGE:
            any_valid_relative = False
            for sub in self.angehoerige.entries:
                f = sub.form
                choice = f.adresse_choice.data
                if choice in (-2, -4):
                    any_valid_relative = True
                    continue
                if choice == -1:
                    missing = []
                    for fld in (f.strasse, f.hausnummer, f.plz, f.ort):
                        if not fld.data:
                            fld.errors.append("Erforderlich.")
                            missing.append(fld)
                    if missing:
                        f.adresse_choice.errors.append("Bitte neue Adresse vollständig angeben.")
                        ok = False
                    else:
                        any_valid_relative = True
                    continue
                if choice in (0, -3, None):
                    f.adresse_choice.errors.append(
                        "Bitte „Wie Meldeadresse“, „Wie Auftragsadresse“ oder „Neue Adresse anlegen…“ wählen."
                    )
                    ok = False

            if not any_valid_relative and self.angehoerige.entries:
                first = self.angehoerige.entries[0].form
                first.adresse_choice.errors.append(
                    "Bei Kostenstelle „Angehörige“ muss mindestens ein Angehöriger mit gültiger Adresse angegeben werden."
                )
                ok = False

        return ok

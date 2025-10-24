# app.py
from flask import Flask, render_template, redirect, url_for
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from forms import PatientForm, TBPatientForm
from enum import Enum
from sqlalchemy import Enum as SqlEnum
from models import db, Patient, GeschlechtEnum, Adresse
from faker import Faker
from datetime import date
import random
import click

load_dotenv()

app = Flask(__name__, instance_relative_config=True)

# Stelle sicher, dass instance/ existiert
os.makedirs(app.instance_path, exist_ok=True)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "fallback-key")

db_path = os.path.join(app.instance_path, "site.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
csrf = CSRFProtect(app)

@app.route("/")
def home():
    return render_template("home.html")

# Todesbescheinigung (TB) #

@app.route("/tb/new", methods=["GET", "POST"])
def tb_new():
    form = TBPatientForm()

    # Choices für vorhandene Adressen befüllen (+ „Neu…“ Option)
    adressen = Adresse.query.order_by(Adresse.ort, Adresse.plz, Adresse.strasse, Adresse.hausnummer).all()
    form.meldeadresse_id.choices = [(-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]

    if form.validate_on_submit():
        # Entweder existierende Adresse…
        if form.meldeadresse_id.data != -1:
            adr = Adresse.query.get(form.meldeadresse_id.data)
            if not adr:
                # Fallback: sollte eigentlich nicht passieren
                return render_template("tb_new.html", form=form, error="Adresse nicht gefunden.")
        else:
            # …oder neue Adresse anlegen (validiere minimal)
            missing = [f for f in ("new_strasse", "new_hausnummer", "new_plz", "new_ort")
                       if not getattr(form, f).data]
            if missing:
                # einfache Fehlermeldung – alternativ Feldfehler setzen
                return render_template("tb_new.html", form=form, error="Bitte alle Adressfelder ausfüllen.")
            adr = Adresse(
                strasse=form.new_strasse.data,
                hausnummer=form.new_hausnummer.data,
                plz=form.new_plz.data,
                ort=form.new_ort.data,
            )
            db.session.add(adr)
            db.session.flush()  # damit adr.id verfügbar ist


        p = Patient()
        form.populate_obj(p)
        p.meldeadresse = adr
        db.session.add(p)
        db.session.commit()
        return redirect(url_for("patient_overview"))
    return render_template("tb_new.html", form=form)

# Patients #

@app.route("/patient/overview")
def patient_overview():
    patients = Patient.query.order_by(Patient.name, Patient.vorname).all()
    return render_template("patient_overview.html", patients=patients)

@app.route("/patient/new", methods=["GET", "POST"])
def patient_new():
    form = PatientForm()
    if form.validate_on_submit():
        p = Patient()
        form.populate_obj(p)
        db.session.add(p)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("patient_new.html", form=form)



def seed_faker(n_addresses=15, n_patients=20):

    fake = Faker("de_DE")

    adrs = []
    for _ in range(n_addresses):
        a = Adresse(
            strasse=fake.street_name(),
            hausnummer=fake.building_number(),
            plz=fake.postcode(),
            ort=fake.city()
            # distanz=random.randint(1, 60),  # z.B. km
        )
        db.session.add(a)
        adrs.append(a)

    # IDs holen ohne Commit (damit Beziehung sofort gesetzt werden kann)
    db.session.flush()

    genders = list(GeschlechtEnum)
    for _ in range(n_patients):
        geburtsname = fake.last_name() if random.random() < 0.25 else None
        p = Patient(
            name=fake.last_name(),
            geburtsname=geburtsname,
            vorname=fake.first_name(),
            geburtsdatum=fake.date_between(start_date="-90y", end_date="-1y"),
            geschlecht=random.choice(genders),
            meldeadresse=random.choice(adrs)
        )
        db.session.add(p)

    db.session.commit()
    click.echo(f"OK ✓  {n_addresses} Adressen und {n_patients} Patienten angelegt.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
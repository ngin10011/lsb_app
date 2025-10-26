# app.py
from flask import Flask, render_template, redirect, url_for
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from forms import PatientForm, TBPatientForm
from enum import Enum
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from models import (db, Patient, GeschlechtEnum, Adresse, 
                    Auftrag, KostenstelleEnum)
from faker import Faker
from datetime import date
import random
import click
from seed import seed_faker

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

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, conn_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

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

        # --- NEU: Auftrag für diesen Patient ---
        a = Auftrag(
            auftragsnummer=form.auftragsnummer.data,
            auftragsdatum=form.auftragsdatum.data,
            auftragsuhrzeit=form.auftragsuhrzeit.data,
            kostenstelle=form.kostenstelle.data,   # bereits Enum dank coerce
            mehraufwand=bool(form.mehraufwand.data),
            bemerkung=form.bemerkung.data,
            patient=p,  # 1:1 Verknüpfung
        )

        try:
            db.session.add(p)  # a hängt via relationship dran (cascade)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # z.B. doppelte Auftragsnummer
            form.auftragsnummer.errors.append("Auftragsnummer bereits vergeben.")
            return render_template("tb_new.html", form=form)

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


@app.cli.command("seed-faker")
@click.option("--n-addresses", default=10, show_default=True, help="Anzahl Adressen")
@click.option("--n-patients",  default=20, show_default=True, help="Anzahl Patienten")
@click.option("--no-deterministic", is_flag=True, help="Echter Zufall (nicht reproduzierbar)")
@click.option("--reset", is_flag=True, help="Drop+Create der Tabellen vor dem Seeding")
def seed_faker_cmd(n_addresses, n_patients, no_deterministic, reset):
    """Beispieldaten erzeugen (Adressen, Patienten, Aufträge)."""
    # App-Kontext ist durch Flask-CLI bereits aktiv
    seed_faker(
        n_addresses=n_addresses,
        n_patients=n_patients,
        deterministic=not no_deterministic,
        reset=reset,
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
# app.py
from flask import Flask, render_template, redirect, url_for
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from forms import PatientForm
from enum import Enum
from sqlalchemy import Enum as SqlEnum
from models import db, Patient

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
    form = PatientForm()
    if form.validate_on_submit():
        p = Patient()
        form.populate_obj(p)
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
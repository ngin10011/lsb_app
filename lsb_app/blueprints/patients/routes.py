# lsb_app/blueprints/patients/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy import case, asc, desc
from sqlalchemy.orm import selectinload
from lsb_app.blueprints.patients import bp
from lsb_app.extensions import db
from lsb_app.models import Patient, Auftrag, AuftragsStatusEnum
from lsb_app.forms import PatientForm
from lsb_app.models.adresse import Adresse

@bp.route("/", methods=["GET"])
def overview():
    # Query-Parameter
    status_param = request.args.get("status", "").strip()         # z. B. READY
    sort_param   = request.args.get("sort", "auftragsnummer").strip()  # auftragsnummer | name | status
    dir_param    = request.args.get("dir", "desc").strip()         # asc | desc

    # Basismenge mit Join u. Eager Loading
    q = (
        db.session.query(Patient)
        .outerjoin(Auftrag, Patient.id == Auftrag.patient_id)
        .options(
            selectinload(Patient.meldeadresse),
            selectinload(Patient.auftrag).selectinload(Auftrag.auftragsadresse),
            selectinload(Patient.auftrag).selectinload(Auftrag.bestattungsinstitut),
            selectinload(Patient.auftrag).selectinload(Auftrag.behoerden),
            selectinload(Patient.angehoerige),
        )
    )

    # Status-Filter
    if status_param:
        try:
            q = q.filter(Auftrag.status == AuftragsStatusEnum(status_param))
        except Exception:
            # Ungültiger Wert: kein Filter anwenden
            pass

    # Sortierrichtung validieren
    dir_param = dir_param if dir_param in {"asc", "desc"} else "asc"
    order = []

    # Hilfs-Ausdruck: NULLS LAST für Felder aus Auftrag
    nulls_last_num = case((Auftrag.auftragsnummer.is_(None), 1), else_=0)
    nulls_last_dat = case((Auftrag.auftragsdatum.is_(None), 1), else_=0)

    if sort_param == "name":
        # Name, sekundär Auftragsnummer (NULLS LAST)
        order.append(asc(Patient.name) if dir_param == "asc" else desc(Patient.name))
        order.append(asc(nulls_last_num))
        order.append(asc(Auftrag.auftragsnummer))
    elif sort_param == "status":
        # Status definierte Ordnung, sekundär Auftragsnummer (NULLS LAST)
        status_order = [
            AuftragsStatusEnum.TODO,
            AuftragsStatusEnum.WAIT,
            AuftragsStatusEnum.READY,
            AuftragsStatusEnum.SENT,
            AuftragsStatusEnum.DONE,
        ]
        status_case = case({s: i for i, s in enumerate(status_order)},
                           value=Auftrag.status, else_=999)
        order.append(asc(status_case) if dir_param == "asc" else desc(status_case))
        order.append(asc(nulls_last_num))
        order.append(asc(Auftrag.auftragsnummer))
    else:
        # Standard: Auftragsnummer (NULLS LAST)
        order.append(asc(nulls_last_num))
        primary = asc(Auftrag.auftragsnummer) if dir_param == "asc" else desc(Auftrag.auftragsnummer)
        order.append(primary)
        # Sekundär stabilisieren: Name
        order.append(asc(Patient.name))

    for oe in order:
        q = q.order_by(oe)

    patients = q.all()

    status_choices = [("", "— alle —")] + [(s.value, s.value) for s in AuftragsStatusEnum]

    return render_template(
        "patients/overview.html",
        patients=patients,
        status_choices=status_choices,
        selected_status=status_param,
        sort=sort_param,
        dir=dir_param,
    )

@bp.route("/<int:pid>", methods=["GET", "POST"])
def detail(pid: int):
    patient = Patient.query.get_or_404(pid)
    form = PatientForm(obj=patient)

    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(patient)
        try:
            db.session.commit()
            flash("Patient gespeichert.", "success")
            return redirect(url_for("patients.detail", pid=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("patients/detail.html", patient=patient, form=form)

@bp.route("/<int:pid>/edit", methods=["GET", "POST"])
def edit(pid: int):
    patient = (
        db.session.query(Patient)
        .options(
            selectinload(Patient.meldeadresse),
            selectinload(Patient.auftrag),
        )
        .get(pid)
    )
    if not patient:
        abort(404)

    form = PatientForm(obj=patient)

    # # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.meldeadresse_id.choices = [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.meldeadresse_id.data = patient.meldeadresse_id

    if form.validate_on_submit():
        # WTForms-Felder -> Model
        patient.name = form.name.data
        patient.geburtsname = form.geburtsname.data
        patient.vorname = form.vorname.data
        patient.geburtsdatum = form.geburtsdatum.data
        patient.geschlecht = form.geschlecht.data

        patient.meldeadresse = db.session.get(Adresse, form.meldeadresse_id.data)

        try:
            db.session.commit()
            flash("Patient gespeichert.", "success")
            next_url = request.args.get("next") or url_for("patients.detail", pid=patient.id)
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("patients/edit.html", form=form, patient=patient)
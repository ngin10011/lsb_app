# lsb_app/blueprints/patients/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy import asc, desc
from sqlalchemy.orm import selectinload
from lsb_app.blueprints.patients import bp
from lsb_app.extensions import db
from lsb_app.models import Patient
from lsb_app.forms import PatientForm

@bp.route("/", methods=["GET"])
def overview():
    # einfache serverseitige Suche/Sortierung/Pagination
    q = request.args.get("q", "", type=str).strip()
    sort = request.args.get("sort", "name")
    order = request.args.get("order", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Patient.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Patient.name.ilike(like)) | (Patient.vorname.ilike(like))
        )

    sort_col = getattr(Patient, sort, Patient.name)
    query = query.order_by(asc(sort_col) if order == "asc" else desc(sort_col))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "patients/overview.html",
        pagination=pagination,
        patients=pagination.items,
        q=q,
        sort=sort,
        order=order,
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

    if form.validate_on_submit():
        # WTForms-Felder -> Model
        patient.name = form.name.data
        patient.geburtsname = form.geburtsname.data
        patient.vorname = form.vorname.data
        patient.geburtsdatum = form.geburtsdatum.data
        patient.geschlecht = form.geschlecht.data  # Enum via coerce

        try:
            db.session.commit()
            flash("Patient gespeichert.", "success")
            next_url = request.args.get("next") or url_for("patients.detail", pid=patient.id)
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("patients/edit.html", form=form, patient=patient)
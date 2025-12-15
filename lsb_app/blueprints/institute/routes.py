# lsb_app/blueprints/institute/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy import or_
from lsb_app.blueprints.institute import bp
from lsb_app.extensions import db
from lsb_app.models.institut import Bestattungsinstitut
from lsb_app.models import Adresse, Auftrag
from lsb_app.forms import InstitutForm

@bp.route("/<int:iid>/edit", methods=["GET", "POST"])
def edit(iid: int):
    inst = db.session.get(Bestattungsinstitut, iid)
    if not inst:
        abort(404)

    form = InstitutForm(obj=inst)

    # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.adresse_id.choices = [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.adresse_id.data = inst.adresse_id

    if form.validate_on_submit():
        inst.kurzbezeichnung = form.kurzbezeichnung.data
        inst.firmenname = form.firmenname.data
        inst.email = form.email.data
        inst.bemerkung = form.bemerkung.data
        inst.anschreibbar = bool(form.anschreibbar.data)

        inst.adresse = db.session.get(Adresse, form.adresse_id.data)
        inst.rechnungadress_modus = form.rechnungadress_modus.data

        try:
            db.session.commit()
            flash("Bestattungsinstitut gespeichert.", "success")
            return redirect(request.args.get("next") or url_for("patients.overview"))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("institute/edit.html", form=form, institut=inst)

@bp.route("/new", methods=["GET", "POST"])
def create():
    # Kontext: an welchen Auftrag soll es gehängt werden?
    aid = request.args.get("aid", type=int)
    if not aid:
        abort(400, description="Missing aid (auftrag_id)")

    auftrag = db.session.get(Auftrag, aid)
    if not auftrag:
        abort(404)

    form = InstitutForm()

    # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.adresse_id.choices = [(a.id, str(a)) for a in adressen]

    if form.validate_on_submit():
        inst = Bestattungsinstitut(
            kurzbezeichnung=form.kurzbezeichnung.data,
            firmenname=form.firmenname.data,
            email=form.email.data,
            bemerkung=form.bemerkung.data,
            anschreibbar=bool(form.anschreibbar.data),
            adresse_id=form.adresse_id.data,
            rechnungadress_modus=form.rechnungadress_modus.data,
        )

        db.session.add(inst)
        db.session.flush()  # inst.id verfügbar ohne commit

        # Auftrag direkt verknüpfen
        auftrag.bestattungsinstitut_id = inst.id

        try:
            db.session.commit()
            flash("Bestattungsinstitut angelegt und dem Auftrag zugeordnet.", "success")
            return redirect(request.args.get("next") or url_for("patients.overview"))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("institute/edit.html", form=form, institut=None)

@bp.route("/", methods=["GET"])
def overview():
    q = (request.args.get("q") or "").strip()

    query = Bestattungsinstitut.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Bestattungsinstitut.kurzbezeichnung.ilike(like),
                Bestattungsinstitut.firmenname.ilike(like),
                Bestattungsinstitut.email.ilike(like),
            )
        )

    institute = query.order_by(
        Bestattungsinstitut.kurzbezeichnung.asc(),
        Bestattungsinstitut.firmenname.asc(),
    ).all()

    return render_template("institute/overview.html", institute=institute, q=q)

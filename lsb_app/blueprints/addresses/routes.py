# lsb_app/blueprints/addresses/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.addresses import bp
from lsb_app.extensions import db
from lsb_app.models import Adresse
from lsb_app.forms import AddressForm

@bp.route("/<int:aid>/edit", methods=["GET", "POST"])
def edit(aid: int):
    adr = db.session.get(Adresse, aid)
    if not adr:
        abort(404)

    form = AddressForm(obj=adr)

    if form.validate_on_submit():
        adr.strasse = form.strasse.data
        adr.hausnummer = form.hausnummer.data
        adr.plz = form.plz.data
        adr.ort = form.ort.data

        try:
            db.session.commit()
            flash("Adresse gespeichert.", "success")
            next_url = request.args.get("next") or url_for("patients.overview")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("addresses/edit.html", form=form, adresse=adr)

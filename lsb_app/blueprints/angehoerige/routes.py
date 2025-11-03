from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.angehoerige import bp
from lsb_app.extensions import db
from lsb_app.models import Angehoeriger
from lsb_app.models.adresse import Adresse
from lsb_app.forms import AngehoerigerForm

@bp.route("/<int:angid>/edit", methods=["GET", "POST"])
def edit(angid: int):
    ang = db.session.get(Angehoeriger, angid)
    if not ang:
        abort(404)

    # form = InstitutForm(obj=inst)
    form = AngehoerigerForm(obj=ang)

    # # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.adresse_id.choices = [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.adresse_id.data = ang.adresse_id

    if form.validate_on_submit():
        ang.name = form.name.data
        ang.vorname = form.vorname.data
        ang.geschlecht = form.geschlecht.data
        ang.verwandtschaftsgrad = form.verwandtschaftsgrad.data
        ang.telefonnummer = form.telefonnummer.data
        ang.email = form.email.data

        ang.adresse = db.session.get(Adresse, form.adresse_id.data)

        try:
            db.session.commit()
            flash("Angehoeriger gespeichert.", "success")
            return redirect(request.args.get("next") or url_for("patients.overview"))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("angehoerige/edit.html", form=form, angehoeriger=ang)

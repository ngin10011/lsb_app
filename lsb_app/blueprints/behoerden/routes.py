from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.behoerden import bp
from lsb_app.extensions import db
from lsb_app.models import Behoerde
from lsb_app.models.adresse import Adresse
from lsb_app.forms import BehoerdeForm

@bp.route("/<int:bid>/edit", methods=["GET", "POST"])
def edit(bid: int):
    beh = db.session.get(Behoerde, bid)
    if not beh:
        abort(404)

    form = BehoerdeForm(obj=beh)

    # # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.adresse_id.choices = [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.adresse_id.data = beh.adresse_id

    if form.validate_on_submit():
        beh.name = form.name.data
        beh.email = form.email.data
        beh.bemerkung = form.bemerkung.data

        beh.adresse = db.session.get(Adresse, form.adresse_id.data)

        try:
            db.session.commit()
            flash("Behörde gespeichert.", "success")
            return redirect(request.args.get("next") or url_for("patients.overview"))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("behoerden/edit.html", form=form, behoerde=beh)

from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.institute import bp
from lsb_app.extensions import db
from lsb_app.models.institut import Bestattungsinstitut
from lsb_app.models.adresse import Adresse
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
    form.adresse_id.choices = [(0, "— keine Adresse —")] + [(a.id, str(a)) for a in adressen]
    form.adresse_id.data = inst.adresse_id or 0

    if form.validate_on_submit():
        inst.kurzbezeichnung = form.kurzbezeichnung.data
        inst.firmenname = form.firmenname.data
        inst.email = form.email.data
        inst.bemerkung = form.bemerkung.data
        inst.anschreibbar = bool(form.anschreibbar.data)

        sel = form.adresse_id.data or 0
        inst.adresse = db.session.get(Adresse, sel) if sel > 0 else None

        try:
            db.session.commit()
            flash("Bestattungsinstitut gespeichert.", "success")
            return redirect(request.args.get("next") or url_for("patients.overview"))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("institute/edit.html", form=form, institut=inst)

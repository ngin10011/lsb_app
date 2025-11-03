# lsb_app/blueprints/auftraege/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.auftraege import bp
from lsb_app.extensions import db
from lsb_app.models import Auftrag
from lsb_app.forms import AuftragForm
from lsb_app.models.adresse import Adresse

@bp.route("/<int:aid>/edit", methods=["GET", "POST"], endpoint="edit")
def edit(aid: int):
    auftrag = db.session.get(Auftrag, aid)
    if not auftrag:
        abort(404)

    form = AuftragForm(obj=auftrag)

    # # Adressauswahl
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    form.auftragsadresse_id.choices = [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.auftragsadresse_id.data = auftrag.auftragsadresse_id

    if form.validate_on_submit():
        auftrag.auftragsnummer  = form.auftragsnummer.data
        auftrag.auftragsdatum   = form.auftragsdatum.data
        auftrag.auftragsuhrzeit = form.auftragsuhrzeit.data
        auftrag.kostenstelle    = form.kostenstelle.data
        auftrag.status          = form.status.data
        auftrag.mehraufwand     = bool(form.mehraufwand.data)
        auftrag.bemerkung       = form.bemerkung.data

        auftrag.auftragsadresse = db.session.get(Adresse, form.auftragsadresse_id.data)

        try:
            db.session.commit()
            flash("Auftrag gespeichert.", "success")
            next_url = request.args.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(url_for("patients.detail", pid=auftrag.patient_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("auftraege/edit.html", form=form, auftrag=auftrag)

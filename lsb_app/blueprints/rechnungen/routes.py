# lsb_app/blueprints/invoices/routes.py
from flask import url_for, current_app, render_template, request, flash, send_file, redirect
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import Rechnung, Auftrag, AuftragsStatusEnum
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm
from datetime import date
from weasyprint import HTML
from pathlib import Path
from lsb_app.forms import RechnungForm
from lsb_app.extensions import db
from decimal import Decimal

@bp.route("/<int:aid>/create", methods=["GET", "POST"])
def create(aid):
    auftrag = Auftrag.query.get_or_404(aid)
    form = RechnungForm()

    if form.validate_on_submit():
        rechnung = Rechnung(
            version=1,  # oder was immer deine Startversion ist
            art=form.art.data,  # ist schon RechnungsArtEnum dank coerce
            rechnungsdatum=form.rechnungsdatum.data,  # datetime.date
            bemerkung=form.bemerkung.data,  # str oder None
            betrag=Decimal("0.00"),  # TODO: hier später sinnvoll berechnen
            auftrag=auftrag,  # setzt automatisch auftrag_id
        )

        db.session.add(rechnung)
        db.session.commit()

        flash("Rechnung wurde gespeichert.", "success")
        return redirect(url_for("patients.detail", pid=auftrag.patient_id))

    return render_template("rechnungen/create.html", auftrag=auftrag, form=form)

@bp.get("/<int:aid>")
def rechnung(aid):
    auftrag = Auftrag.query.get_or_404(aid)

    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=date.today()
    )
    return render_template("rechnungen/standard.html", vm=vm)

@bp.get("/<int:aid>/pdf")
def rechnung_pdf(aid: int):
    auftrag = Auftrag.query.get_or_404(aid)

    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=date.today()
    )

    # 1) HTML rendern
    html_str = render_template("rechnungen/standard.html", vm=vm)

    # 2) Basis-URL setzen, damit /static/... im Template korrekt aufgelöst wird
    #    request.host_url -> http://localhost:5000/  (funktioniert mit url_for-Pfaden)
    base_url = request.host_url

    # 3) PDF erzeugen
    pdf_bytes = HTML(string=html_str, base_url=base_url).write_pdf()

    # 4) Dateinamen & Speicherort bestimmen
    filename = f"Rechnung_{auftrag.auftragsnummer}.pdf"
    save_dir = Path(current_app.instance_path) / "invoices"
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / filename

    # 5) Speichern
    file_path.write_bytes(pdf_bytes)

    # 6) Direkt im Browser anzeigen (kein Download-Zwang)
    return send_file(
        path_or_file=str(file_path),
        mimetype="application/pdf",
        download_name=filename,
        as_attachment=False,
        max_age=0,
    )

# lsb_app/blueprints/invoices/routes.py
from flask import Blueprint, current_app, render_template, request, Response, send_file
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import Patient, Auftrag, AuftragsStatusEnum
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm
from datetime import date
from weasyprint import HTML
from pathlib import Path

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

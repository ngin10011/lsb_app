# lsb_app/blueprints/invoices/routes.py
from flask import (url_for, current_app, render_template, request, flash, send_file, 
                   redirect, abort)
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import Rechnung, Auftrag, AuftragsStatusEnum, RechnungsStatusEnum
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm
from datetime import date
from weasyprint import HTML
from pathlib import Path
from lsb_app.forms import RechnungForm, RechnungCreateForm
from lsb_app.extensions import db
from decimal import Decimal

def generate_and_save_rechnung_pdf(rechnung: Rechnung) -> Path:
    """Erzeugt das PDF für eine Rechnung und speichert es im instance-/invoices-Ordner.
       Gibt den Pfad zur Datei zurück.
    """
    auftrag = rechnung.auftrag

    # ViewModel auf Basis des Auftrags + Rechnungsdatum der Rechnung
    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=rechnung.rechnungsdatum,
    )

    # HTML rendern
    html_str = render_template("rechnungen/standard.html", vm=vm)

    # Basis-URL (für static-Dateien im Template)
    base_url = request.host_url

    # PDF erzeugen
    pdf_bytes = HTML(string=html_str, base_url=base_url).write_pdf()

    # Speicherort
    save_dir = Path(current_app.instance_path) / "invoices"
    save_dir.mkdir(parents=True, exist_ok=True)

    # Dateiname z. B. mit Versionsnummer
    filename = f"Rechnung_{auftrag.auftragsnummer}_v{rechnung.version}.pdf"
    file_path = save_dir / filename

    file_path.write_bytes(pdf_bytes)
    return file_path


@bp.route("/<int:aid>/create", methods=["GET", "POST"])
def create(aid):
    auftrag = Auftrag.query.get_or_404(aid)
    existing_invoices = auftrag.rechnungen

    form = RechnungCreateForm()

    if form.validate_on_submit():


        try:
            # 1) Höchste Version ermitteln
            max_version = max((r.version for r in auftrag.rechnungen), default=0)
            neue_version = max_version + 1

            # 2) Betrag über das bestehende ViewModel berechnen
            vm = build_rechnung_vm(
                auftrag=auftrag,
                cfg=current_app.config,
                rechnungsdatum=form.rechnungsdatum.data,
            )
            betrag = Decimal(vm.summe_str.replace(",", "."))

            # 3) Rechnung in der DB anlegen
            rechnung = Rechnung(
                version=neue_version, 
                art=form.art.data, 
                rechnungsdatum=form.rechnungsdatum.data, 
                bemerkung=form.bemerkung.data,  
                betrag=betrag,  
                auftrag=auftrag, 
                status=RechnungsStatusEnum.CREATED,
            )

            db.session.add(rechnung)
            db.session.flush() # rechnung.id ist jetzt gesetzt

            # 4) PDF erzeugen & speichern (auf Basis der gespeicherten Rechung)
            pdf_path = generate_and_save_rechnung_pdf(rechnung)

            rechnung.pdf_path = str(pdf_path)

            db.session.commit()

        except Exception as e:
            # ➤ Logging für Entwickler
            current_app.logger.exception("Fehler bei der Rechnungserstellung")

            # ➤ DB zurückrollen
            db.session.rollback()

            # ➤ Benutzerfeedback
            flash(f"Beim Erstellen der Rechnung ist ein Fehler aufgetreten: {e}", "danger")

            # Optional: Fehler weitergeben für Debugger
            # raise

            # ➤ Wieder Seite rendern
            return render_template(
                "rechnungen/create.html",
                auftrag=auftrag,
                form=form,
                existing_invoices=existing_invoices,
                neue_version=(max((r.version for r in existing_invoices), default=0) + 1),
            )

        # 5) UI-Rückmeldung und Redirect
        if form.submit_generate.data:
            flash(f"Rechnung wurde gespeichert und PDF erstellt unter {pdf_path}.", "success")
            return redirect(url_for("patients.detail", pid=auftrag.patient_id))
        
    max_version = max((r.version for r in existing_invoices), default=0)
    neue_version = max_version + 1

    return render_template(
        "rechnungen/create.html", 
        auftrag=auftrag, 
        form=form, 
        existing_invoices=existing_invoices,
        neue_version=neue_version)

@bp.route("/<int:rid>/edit", methods=["GET", "POST"])
def edit(rid: int):
    inv = db.session.get(Rechnung, rid)
    if not inv:
        abort(404)

    form = RechnungForm(obj=inv)

    # if form.validate_on_submit():
    #     rechnung = Rechnung(
    #         version=1,  # oder was immer deine Startversion ist
    #         art=form.art.data,  # ist schon RechnungsArtEnum dank coerce
    #         status=form.status.data,
    #         rechnungsdatum=form.rechnungsdatum.data,  # datetime.date
    #         bemerkung=form.bemerkung.data,  # str oder None
    #         betrag=Decimal("0.00"),  # TODO: hier später sinnvoll berechnen
    #         auftrag=inv.auftrag,  # setzt automatisch auftrag_id
    #     )

    #     db.session.add(rechnung)
    #     db.session.commit()

    #     flash("Rechnung wurde gespeichert.", "success")
    #     return redirect(url_for("patients.detail", pid=inv.auftrag.patient_id))
    
    if form.validate_on_submit():
            inv.art=form.art.data  # ist schon RechnungsArtEnum dank coerce
            inv.status=form.status.data
            inv.rechnungsdatum=form.rechnungsdatum.data  # datetime.date
            inv.bemerkung=form.bemerkung.data  # str oder None

            try:
                db.session.commit()
                flash("Rechnung gespeichert.", "success")
                return redirect(url_for("patients.detail", pid=inv.auftrag.patient_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template("rechnungen/edit.html", rechnung=inv, form=form)

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

# lsb_app/blueprints/invoices/routes.py
from flask import (url_for, current_app, render_template, request, flash, send_file, 
                   redirect, abort)
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import (Rechnung, Auftrag, AuftragsStatusEnum, RechnungsStatusEnum,
                            RechnungsArtEnum, KostenstelleEnum)
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm
from datetime import date
from weasyprint import HTML
from pathlib import Path
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from lsb_app.services.auftrag_filters import ready_for_email_filter
from lsb_app.forms import RechnungForm, RechnungCreateForm
from lsb_app.extensions import db
from decimal import Decimal
import smtplib
from email.message import EmailMessage
import imaplib
from email.utils import formatdate
import time
import mimetypes
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


def generate_and_save_rechnung_pdf(rechnung: Rechnung) -> Path:
    """Erzeugt das PDF für eine Rechnung und speichert es im instance-/invoices-Ordner.
       Gibt den Pfad zur Datei zurück.
    """
    
    auftrag = rechnung.auftrag

    if rechnung.art == RechnungsArtEnum.MAHNUNG:
        rechnungsart_str = "MAHNUNG"
    else:
        rechnungsart_str = "RECHNUNG"
    # rechnungsart = getattr(rechnung.art, "value", rechnung.art)

    # ViewModel auf Basis des Auftrags + Rechnungsdatum der Rechnung
    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=rechnung.rechnungsdatum,
        # rechnungsart=rechnung.art,
        rechnungsart=rechnungsart_str,
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

def create_rechnung_for_auftrag(
    auftrag: Auftrag,
    art: RechnungsArtEnum | None = None,
    rechnungsdatum: date | None = None,
    bemerkung: str | None = None,
) -> Rechnung:
    """
    Legt IMMER eine neue Rechnung für den Auftrag an:
    - Version = max(version) + 1
    - Betrag über build_rechnung_vm
    - Status = CREATED
    - PDF wird erzeugt, pdf_path gesetzt
    -> Gibt die Rechnung zurück (noch nicht committed).

    Später kannst du hier drin die Logik erweitern
    (z.B. nicht neu erstellen, wenn schon SENT etc.).
    """
    if art is None:
        art = RechnungsArtEnum.ERSTRECHNUNG
    if rechnungsdatum is None:
        rechnungsdatum = date.today()

    # 1) Höchste Version ermitteln
    max_version = max((r.version for r in auftrag.rechnungen), default=0)
    neue_version = max_version + 1
    logger.info(
        "create_rechnung_for_auftrag: neue Version – auftrag_id=%s, version=%s",
        auftrag.id,
        neue_version,
    )

    # 2) Betrag über ViewModel berechnen
    vm = build_rechnung_vm(
        auftrag=auftrag,
        cfg=current_app.config,
        rechnungsdatum=rechnungsdatum,
        rechnungsart=art.value,
    )
    betrag = Decimal(vm.summe_str.replace(",", "."))

    # 3) Rechnung in der DB anlegen (noch ohne PDF)
    rechnung = Rechnung(
        version=neue_version,
        art=art,
        rechnungsdatum=rechnungsdatum,
        bemerkung=bemerkung,
        betrag=betrag,
        auftrag=auftrag,
        status=RechnungsStatusEnum.CREATED,
    )

    db.session.add(rechnung)
    db.session.flush()  # rechnung.id ist jetzt gesetzt

    # 4) PDF erzeugen & pfad setzen
    pdf_path = generate_and_save_rechnung_pdf(rechnung)
    rechnung.pdf_path = str(pdf_path)

    logger.info(
        "create_rechnung_for_auftrag: Rechnung erstellt – rechnung_id=%s, pdf_path=%s",
        rechnung.id,
        rechnung.pdf_path,
    )

    return rechnung

def determine_email_for_auftrag(auftrag: Auftrag) -> str | None:
    """
    Wählt basierend auf der Kostenstelle die passende E-Mail-Adresse:
    - BESTATTUNGSINSTITUT -> E-Mail des Instituts
    - ANGEHOERIGE         -> erste Angehörigen-E-Mail
    - BEHOERDE            -> erste Behörden-E-Mail
    """
    kostenstelle = auftrag.kostenstelle

    if kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT:
        if auftrag.bestattungsinstitut and auftrag.bestattungsinstitut.email:
            return auftrag.bestattungsinstitut.email

    if kostenstelle == KostenstelleEnum.ANGEHOERIGE and auftrag.patient:
        for ang in auftrag.patient.angehoerige:
            if ang.email:
                return ang.email

    if kostenstelle == KostenstelleEnum.BEHOERDE:
        for beh in auftrag.behoerden:
            if beh.email:
                return beh.email

    return None

def send_invoice_email(
    rechnung: Rechnung,
    recipient_email: str,
) -> None:
    """
    Versendet die Rechnung als E-Mail mit PDF-Anhang und legt sie im IMAP-"Sent"-Ordner ab.
    
    - SMTP/IMAP-Konfiguration wird aus current_app.config gelesen.
    - attachment_filename: optionaler Dateiname für den Anhang.
      Falls None, wird der Dateiname aus rechnung.pdf_path verwendet.
    """

    cfg = current_app.config

    EMAIL_ADDRESS = cfg.get("MAIL_USERNAME")
    EMAIL_PASSWORD = cfg.get("MAIL_PASSWORD")
    SMTP_SERVER = cfg.get("MAIL_SERVER", "smtp.mail.de")
    SMTP_PORT = int(cfg.get("MAIL_PORT", 465))  # SSL-Port (z. B. 465)
    IMAP_SERVER = cfg.get("MAIL_IMAP_SERVER", cfg.get("IMAP_SERVER", "imap.mail.de"))

    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, IMAP_SERVER]):
        logger.error("Mail-Konfiguration unvollständig, Versand abgebrochen.")
        raise RuntimeError("Mail-Konfiguration ist unvollständig.")

    if not rechnung.pdf_path:
        raise RuntimeError("Rechnung hat keinen pdf_path – PDF muss vorher erzeugt werden.")

    dateipfad = Path(rechnung.pdf_path)
    if not dateipfad.is_file():
        raise FileNotFoundError(f"PDF-Datei nicht gefunden: {dateipfad}")

    # --- E-Mail zusammenbauen ---
    betreff = f"Rechnung {rechnung.auftrag.auftragsnummer} – Leichenschau"

    text = (
        "Sehr geehrte Damen und Herren,\n\n"
        "anbei erhalten Sie die Rechnung zur durchgeführten Leichenschau.\n\n"
        "Mit freundlichen Grüßen\n"
        f"{cfg.get('COMPANY_NAME', '')}"
    )

    filename = f"Rechnung_{rechnung.auftrag.auftragsnummer}.pdf"
    logger.info(
        "Starte E-Mail-Versand an %s mit Anhang: %s",
        recipient_email,
        filename,
    )

    msg = EmailMessage()
    msg["Subject"] = betreff
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    msg.set_content(text)

    mime_type, _ = mimetypes.guess_type(str(dateipfad))
    mime_type = mime_type or "application/pdf"
    main_type, sub_type = mime_type.split("/")

    
    with dateipfad.open("rb") as f:
        file_data = f.read()
        msg.add_attachment(
            file_data,
            maintype=main_type,
            subtype=sub_type,
            filename=filename,
        )

    # --- SMTP-Versand (wie in deiner anderen App: SMTP_SSL) ---
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception:
        logger.exception("Fehler beim SMTP-Versand")
        raise

    # --- IMAP: in "Rechnungen_LS" ablegen (identisch zum bewährten Code) ---
    try:
        time.sleep(1)  # kleiner Delay wie in deiner anderen App
        raw_message = msg.as_bytes()

        with imaplib.IMAP4_SSL(IMAP_SERVER) as imap:
            imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            # imap.append('"Sent"', '\\Seen', imaplib.Time2Internaldate(time.localtime()), raw_message)
            imap.append('"Rechnungen_LS"', '\\Seen', imaplib.Time2Internaldate(time.localtime()), raw_message)

        logger.info(
            "E-Mail für Rechnung %s im IMAP-Sent-Ordner gespeichert.",
            rechnung.id,
        )

    except Exception:
        logger.exception("Fehler beim Speichern der Mail im IMAP-Ordner 'Sent' (IMAP)")
        # Versand war erfolgreich, daher Fehler hier nur loggen


@bp.route("/<int:aid>/create", methods=["GET", "POST"])
def create(aid):
    logger.debug("Rechnung.create aufgerufen, auftrag_id=%s, method=%s", aid, request.method)
    auftrag = Auftrag.query.get_or_404(aid)
    existing_invoices = auftrag.rechnungen

    form = RechnungCreateForm()

    if form.validate_on_submit():


        try:
            # 1) Höchste Version ermitteln
            max_version = max((r.version for r in auftrag.rechnungen), default=0)
            neue_version = max_version + 1
            logger.info(
                "Rechnung.create: berechne neue Version für auftrag_id=%s – max_version=%s, neue_version=%s",
                auftrag.id,
                max_version,
                neue_version,
            )

            # 2) Betrag über das bestehende ViewModel berechnen
            vm = build_rechnung_vm(
                auftrag=auftrag,
                cfg=current_app.config,
                rechnungsdatum=form.rechnungsdatum.data,
                rechnungsart=form.art.data,
            )
            betrag = Decimal(vm.summe_str.replace(",", "."))
            logger.info(
                "Rechnung.create: Betrag berechnet für auftrag_id=%s, version=%s – betrag=%s",
                auftrag.id,
                neue_version,
                betrag,
            )

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
            logger.info(
                "Rechnung.create: Rechnung-Objekt angelegt (noch nicht committet) – rechnung_id=%s, auftrag_id=%s, art=%s, status=%s",
                rechnung.id,
                auftrag.id,
                rechnung.art.name if hasattr(rechnung.art, "name") else rechnung.art,
                rechnung.status.name if hasattr(rechnung.status, "name") else rechnung.status,
            )

            # 4) PDF erzeugen & speichern (auf Basis der gespeicherten Rechung)
            pdf_path = generate_and_save_rechnung_pdf(rechnung)
            rechnung.pdf_path = str(pdf_path)
            logger.info(
                "Rechnung.create: PDF erstellt für rechnung_id=%s, version=%s, pfad=%s",
                rechnung.id,
                rechnung.version,
                rechnung.pdf_path,
            )

            db.session.commit()
            logger.info(
                "Rechnung.create: Commit erfolgreich – rechnung_id=%s, auftrag_id=%s",
                rechnung.id,
                auftrag.id,
            )

        except Exception as e:
            # ➤ Logging für Entwickler
            logger.exception(
                "Fehler bei der Rechnungserstellung – auftrag_id=%s",
                auftrag.id,
            )

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
        
        flash("Rechnung wurde gespeichert und PDF erstellt.", "success")
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

@bp.get("/<int:rid>/pdf")
def show_pdf(rid: int):
    """Bestehendes PDF einer Rechnung anzeigen (ohne es neu zu generieren)."""
    logger.debug("Rechnung.show_pdf aufgerufen, rechnung_id=%s, method=%s", rid, request.method)
    rechnung = db.session.get(Rechnung, rid)
    if not rechnung:
        abort(404)

    if not rechnung.pdf_path:
        logger.warning("show_pdf: Rechnung %s hat keinen pdf_path", rid)
        abort(404)

    file_path = Path(rechnung.pdf_path)

    # Optional: Sicherheit – nur Dateien unter instance/invoices zulassen
    invoices_dir = Path(current_app.instance_path) / "invoices"
    try:
        if not file_path.resolve().is_relative_to(invoices_dir.resolve()):
            logger.error("show_pdf: pdf_path von Rechnung %s zeigt aus dem invoices-Verzeichnis heraus", rid)
            abort(403)
    except AttributeError:
        # falls Python < 3.9, alternativ mit str.startswith arbeiten
        if not str(file_path.resolve()).startswith(str(invoices_dir.resolve())):
            logger.error("show_pdf: pdf_path von Rechnung %s zeigt aus dem invoices-Verzeichnis heraus", rid)
            abort(403)

    if not file_path.is_file():
        logger.warning("show_pdf: PDF-Datei für Rechnung %s nicht gefunden (%s)", rid, file_path)
        abort(404)

    filename = f"Rechnung_{rechnung.auftrag.auftragsnummer}_v{rechnung.version}.pdf"

    return send_file(
        path_or_file=str(file_path),
        mimetype="application/pdf",
        download_name=filename,
        as_attachment=False,   # im Browser anzeigen
        max_age=0,
    )

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

@bp.route("/send-single/<int:auftrag_id>", methods=["POST"])
def send_single_email(auftrag_id: int):
    """
    Verschickt für einen Auftrag eine NEUE Rechnung:
    - neue Rechnung (immer neue Version) + PDF wird erstellt
    - passende E-Mail-Adresse wird ermittelt
    - Versand (Stub)
    """
    auftrag = Auftrag.query.get_or_404(auftrag_id)

    # Optional: nur zulassen, wenn Auftrag in der READY-per-Mail-Menge ist
    if not db.session.query(Auftrag.id).filter(
        and_(Auftrag.id == auftrag_id, ready_for_email_filter())
    ).first():
        flash("Auftrag ist nicht für den E-Mail-Versand READY.", "warning")
        return redirect(url_for("auftraege.ready_email_list"))

    try:
        rechnung = create_rechnung_for_auftrag(auftrag)

        recipient = determine_email_for_auftrag(auftrag)
        if not recipient:
            flash("Keine gültige E-Mail-Adresse gefunden.", "warning")
            return redirect(url_for("auftraege.ready_email_list"))

        send_invoice_email(rechnung, recipient)

        # Optional: Status setzen – für später
        rechnung.status = RechnungsStatusEnum.SENT
        auftrag.status = AuftragsStatusEnum.SENT

        db.session.commit()

        flash(
            f"Rechnung v{rechnung.version} für Auftrag #{auftrag.auftragsnummer or auftrag.id} an {recipient} gesendet.",
            "success",
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception("Fehler beim Einzelversand für auftrag_id=%s", auftrag.id)
        flash(f"Fehler beim Versenden der Rechnung: {exc}", "danger")

    return redirect(url_for("auftraege.ready_email_list"))

@bp.route("/send-batch", methods=["POST"])
def send_batch_email():
    """
    Erzeugt für alle READY-per-E-Mail-Aufträge jeweils eine neue Rechnung + PDF
    und 'versendet' sie (aktuell nur Logging).
    """
    auftraege = (
        db.session.query(Auftrag)
        .filter(ready_for_email_filter())
        .order_by(Auftrag.auftragsdatum.asc())
        .all()
    )

    successes: list[Auftrag] = []
    failures: list[tuple[Auftrag, str]] = []

    for a in auftraege:
        try:
            rechnung = create_rechnung_for_auftrag(a)
            recipient = determine_email_for_auftrag(a)

            if not recipient:
                failures.append((a, "Keine E-Mail-Adresse gefunden"))
                continue

            send_invoice_email(rechnung, recipient)

            rechnung.status = RechnungsStatusEnum.SENT
            a.status = AuftragsStatusEnum.SENT

            successes.append(a)
        except Exception as exc:
            logger.exception("Fehler beim Versand für Auftrag %s", a.id)
            failures.append((a, str(exc)))

    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Fehler beim Commit im Batch-Versand")
        flash(f"Fehler beim Speichern des Versandstatus: {exc}", "danger")
        return redirect(url_for("auftraege.ready_email_list"))

    return render_template(
        "rechnungen/send_batch_result.html",
        successes=successes,
        failures=failures,
    )

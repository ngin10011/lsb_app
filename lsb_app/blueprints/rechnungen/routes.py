# lsb_app/blueprints/rechnungen/routes.py
from flask import (url_for, current_app, render_template, request, flash, send_file, 
                   redirect, abort)
import zipfile
from pypdf import PdfWriter, PdfReader
from lsb_app.blueprints.rechnungen import bp
from lsb_app.models import (Rechnung, Auftrag, AuftragsStatusEnum, RechnungsStatusEnum,
                            RechnungsArtEnum, KostenstelleEnum)
from lsb_app.services.rechnung_vm_factory import build_rechnung_vm, erstelle_anschrift_html_angehoeriger
from datetime import date, datetime, timedelta
from weasyprint import HTML
from pathlib import Path
from sqlalchemy import and_, desc, asc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from lsb_app.services.auftrag_filters import (ready_for_email_filter, ready_for_inquiry_filter,
            has_deliverable_email_filter, ready_for_post_filter)
from lsb_app.forms import RechnungForm, RechnungCreateForm, DummyCSRFForm, PrintBatchToSentForm
from lsb_app.extensions import db
from lsb_app.models import Angehoeriger, Bestattungsinstitut, Behoerde, GeschlechtEnum
from decimal import Decimal
import smtplib
from typing import Optional, Tuple, Union
from email.message import EmailMessage
import imaplib
from lsb_app.services.verlauf import add_verlauf
from email.utils import formatdate
import time
import mimetypes
import logging
logger = logging.getLogger(__name__)

RecipientModel = Union[Angehoeriger, Bestattungsinstitut, Behoerde]

def _zip_pdfs(paths: list[Path], zip_path: Path) -> Path:
    """Erstellt ein ZIP aus PDF-Dateien."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            if p.is_file():
                zf.write(p, arcname=p.name)
            else:
                logger.warning("ZIP: PDF nicht gefunden: %s", p)
    return zip_path

def merge_pdfs(pdf_paths: list[Path], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()

    for p in pdf_paths:
        if not p.is_file():
            logger.warning("merge_pdfs: PDF fehlt: %s", p)
            continue
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)

    with out_path.open("wb") as f:
        writer.write(f)

    return out_path

def determine_recipient_for_auftrag(auftrag: Auftrag) -> tuple[Optional[str], Optional[RecipientModel]]:
    """
    Liefert:
      - die E-Mail-Adresse
      - das zugehörige Empfänger-Objekt (Angehöriger / Institut / Behörde)

    oder (None, None), wenn nichts gefunden wurde.
    """
    kostenstelle = auftrag.kostenstelle

    # Bestattungsinstitut
    if kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT:
        inst = auftrag.bestattungsinstitut
        if inst and inst.email:
            return inst.email, inst

    # Angehörige
    if kostenstelle == KostenstelleEnum.ANGEHOERIGE and auftrag.patient:
        for ang in auftrag.patient.angehoerige:
            if ang.email:
                return ang.email, ang

    # Behörde
    if kostenstelle == KostenstelleEnum.BEHOERDE:
        for beh in auftrag.behoerden:
            if beh.email:
                return beh.email, beh

    return None, None

def build_anrede_for_angehoeriger(ang: Angehoeriger) -> str:
    """
    Erzeugt so etwas wie ' Frau Müller' oder ' Herr Schmidt'.
    Passe das an deine Felder im Angehoeriger-Modell an.
    """
    # Beispiel: falls du ein GeschlechtEnum oder ein Feld 'anrede' hast:
    basis = ""

    if getattr(ang, "geschlecht", None) == GeschlechtEnum.WEIBLICH:
        basis = " Frau"
    elif getattr(ang, "geschlecht", None) == GeschlechtEnum.MAENNLICH:
        basis = "r Herr"

    if basis:
        return f"{basis} {ang.name}"
    else:
        # Fallback
        return f" Damen und Herren"

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

    # Ordnerstruktur nach Jahr/Monat
    rechnungsdatum = rechnung.rechnungsdatum or date.today()
    year = str(rechnungsdatum.year)
    month = f"{rechnungsdatum.month:02d}"

    save_dir = Path(current_app.instance_path) / "invoices" / year / month
    save_dir.mkdir(parents=True, exist_ok=True)

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

    # 0) letzte Rechnung (höchste version) holen
    letzte = (
        db.session.execute(
            select(Rechnung)
            .where(Rechnung.auftrag_id == auftrag.id)
            .order_by(Rechnung.version.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    # 1) Version bestimmen
    max_version = letzte.version if letzte else 0
    neue_version = max_version + 1

    # 1b) Vorgänger canceln (nur wenn vorhanden und "cancelbar")
    if letzte and letzte.status not in {RechnungsStatusEnum.CANCELED}:
        # optional: hier später harte Regeln rein (z.B. SENT/PAID nicht canceln)
        if letzte.status in {RechnungsStatusEnum.CREATED}:  # ggf. erweitern
            letzte.status = RechnungsStatusEnum.CANCELED
            logger.info(
                "create_rechnung_for_auftrag: Vorgänger-Rechnung cancelled – rechnung_id=%s (version=%s)",
                letzte.id, letzte.version
            )
        else:
            logger.info(
                "create_rechnung_for_auftrag: Vorgänger-Rechnung NICHT cancelled (status=%s) – rechnung_id=%s",
                letzte.status, letzte.id
            )

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

def generate_anschreiben_pdf(rechnung: Rechnung) -> Path:
    """
    Erzeugt eine einfache Test-Anschreibenseite (1 Seite).
    """
    auftrag = rechnung.auftrag

    anrede = build_anrede_for_angehoeriger(pick_angehoeriger_for_auftrag(auftrag=auftrag))
    anschrift_html = erstelle_anschrift_html_angehoeriger(auftrag=auftrag)

    html_str = render_template(
        "rechnungen/anschreiben.html",
        anrede=anrede,
        anschrift_html=anschrift_html,
        cfg=current_app.config,
    )

    pdf_bytes = HTML(
        string=html_str,
        base_url=request.host_url,
    ).write_pdf()

    out_dir = Path(current_app.instance_path) / "exports" / "anschreiben"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"Anschreiben_{auftrag.auftragsnummer}_v{rechnung.version}.pdf"
    out_path.write_bytes(pdf_bytes)

    return out_path

@bp.get("/postversand/download/<path:bundle_name>")
def download_postversand_bundle(bundle_name: str):
    bundle_dir = Path(current_app.instance_path) / "exports" / "postversand"
    file_path = bundle_dir / bundle_name

    # Sicherheitscheck: nur Dateien aus diesem Ordner
    try:
        if not file_path.resolve().is_relative_to(bundle_dir.resolve()):
            abort(403)
    except AttributeError:
        if not str(file_path.resolve()).startswith(str(bundle_dir.resolve())):
            abort(403)

    if not file_path.is_file():
        abort(404)

    return send_file(
        str(file_path),
        mimetype="application/pdf",
        download_name=bundle_name,
        as_attachment=True,
        max_age=0,
    )

def pick_angehoeriger_for_auftrag(auftrag: Auftrag) -> Angehoeriger | None:
    if not auftrag.patient or not auftrag.patient.angehoerige:
        return None
    # simple Heuristik: erster Eintrag
    return auftrag.patient.angehoerige[0]

def send_invoice_email(
    rechnung: Rechnung,
    recipient_email: str,
    empfaenger_obj: RecipientModel | None = None,
) -> None:
    """
    Versendet die Rechnung als E-Mail mit PDF-Anhang und legt sie im IMAP-"Sent"-Ordner ab.
    - SMTP/IMAP-Konfiguration wird aus current_app.config gelesen.
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
    
    is_angehoeriger = isinstance(empfaenger_obj, Angehoeriger)
    if is_angehoeriger:
        anrede_angehoerige = build_anrede_for_angehoeriger(empfaenger_obj)

        betreff = "Leichenschau"
        text = (
            f"Sehr geehrte{anrede_angehoerige},\n\n"
            "zunächst mein herzlichstes Beileid zu dem Todesfall in Ihrem Umfeld.\n\n"
            "Es tut mir leid, Sie in dieser schweren Zeit mit der Bürokratie belästigen zu müssen.\n"
            "Ich führte eine Leichenschau zur Ausstellung einer endgültigen Todesbescheinigung durch. "
            "Da mit dem Eintritt des Todes die Leistungspflicht der Krankenkassen endet, "
            "sind die Kosten der Leichenschau von den bestattungspflichtigen Angehörigen zu tragen. "
            "Diese Information können Sie sich gerne von dem für Sie zuständigen Bestattungsunternehmen bestätigen lassen.\n\n"
            f"Im Anhang finden Sie die Rechnung LS-{rechnung.auftrag.auftragsnummer}.\n\n"
            "Beste Grüße\n"
            f"{cfg.get('COMPANY_NAME', '')}"
        )
    else:
        betreff = f"Leichenschau - Rechnung LS-{rechnung.auftrag.auftragsnummer}"
        text = (
            "Sehr geehrte Damen und Herren,\n\n"
            f"anbei erhalten Sie die Rechnung LS-{rechnung.auftrag.auftragsnummer} zur durchgeführten Leichenschau.\n\n"
            "Beste Grüße\n"
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
            imap.append('"Leichenschau/Rechnungen"', '\\Seen', imaplib.Time2Internaldate(time.localtime()), raw_message)

        logger.info(
            "E-Mail für Rechnung %s im IMAP-Ordner 'Rechnungen_LS' gespeichert.",
            rechnung.id,
        )

    except Exception:
        logger.exception("Fehler beim Speichern der Mail im IMAP-Ordner 'Rechnungen_LS' (IMAP)")
        # Versand war erfolgreich, daher Fehler hier nur loggen

def build_inquiry_html_table(auftraege: list[Auftrag]) -> str:
    """
    Baut eine HTML-Tabelle für die Anfrage-Mail mit:
    Leichenschaudatum | Name | Geburtsdatum | Adresse
    """
    rows = []
    for a in auftraege:
        patient = a.patient
        # Leichenschaudatum -> ich nehme hier auftragsdatum
        date_str = a.auftragsdatum.strftime("%d.%m.%Y") if a.auftragsdatum else "—"

        name_str = f"{patient.name}, {patient.vorname}" if patient else "—"

        geburtsdatum = getattr(patient, "geburtsdatum", None)
        geb_str = geburtsdatum.strftime("%d.%m.%Y") if geburtsdatum else "—"

        # Adresse: hier Beispiel über Auftragsadresse
        adr = getattr(a, "auftragsadresse", None)
        if adr:
            addr_str = f"{adr.strasse} {adr.hausnummer}, {adr.plz} {adr.ort}"
        else:
            addr_str = "—"

        rows.append(
            f"""
            <tr>
              <td>{date_str}</td>
              <td>{name_str}</td>
              <td>{geb_str}</td>
              <td>{addr_str}</td>
            </tr>
            """
        )

    rows_html = "\n".join(rows)

    table_html = f"""
    <table border="1" cellspacing="0" cellpadding="4" style="border-collapse: collapse;">
      <thead>
        <tr>
          <th>Leichenschaudatum</th>
          <th>Name</th>
          <th>Geburtsdatum</th>
          <th>Adresse</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    """
    return table_html

def send_inquiry_email(
    institut: Bestattungsinstitut,
    auftraege: list[Auftrag],
) -> None:
    """
    Versendet eine Anfrage an ein Bestattungsinstitut mit einer Tabelle
    der betroffenen Leichenschauen im Mailtext (HTML).
    """

    if not institut.email:
        raise RuntimeError("Bestattungsinstitut hat keine E-Mail-Adresse.")

    cfg = current_app.config

    EMAIL_ADDRESS = cfg.get("MAIL_USERNAME")
    EMAIL_PASSWORD = cfg.get("MAIL_PASSWORD")
    SMTP_SERVER = cfg.get("MAIL_SERVER", "smtp.mail.de")
    SMTP_PORT = int(cfg.get("MAIL_PORT", 465))  # SSL-Port (z. B. 465)
    IMAP_SERVER = cfg.get("MAIL_IMAP_SERVER", cfg.get("IMAP_SERVER", "imap.mail.de"))

    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, IMAP_SERVER]):
        logger.error("Mail-Konfiguration unvollständig, Inquiry-Versand abgebrochen.")
        raise RuntimeError("Mail-Konfiguration ist unvollständig.")

    anzahl = len(auftraege)

    if anzahl == 1:
        ls_phrase = "eine Leichenschau"
        person_phrase = "der folgenden Person"
        rechnung_phrase = "Rechnung"
        todesfall_phrase = "diesen Todesfall"
    else:
        ls_phrase = "Leichenschauen"
        person_phrase = "den folgenden Personen"
        rechnung_phrase = "Rechnungen"
        todesfall_phrase = "diese Todesfälle"

    # --- Tabelle bauen ---
    table_html = build_inquiry_html_table(auftraege)

    betreff = "Anfrage Beauftragung – Leichenschau"

    text_plain = (
        "Sehr geehrte Damen und Herren,\n\n"
        f"bitte teilen Sie mir mit, ob Ihr Institut für {ls_phrase} "
        "beauftragt wurde.\n\n"
        "Eine Übersicht finden Sie in der Tabelle im HTML-Teil dieser E-Mail.\n\n"
        "Vielen Dank und freundliche Grüße\n"
        f"{cfg.get('COMPANY_NAME', '')}\n"
    )


    text_html = f"""
    <p>Sehr geehrte Damen und Herren,</p>
    <p>
      ich führte {ls_phrase} bei {person_phrase} durch. Die Angehörigen
      teilten mir mit, dass sie Ihr Bestattungsinstitut beauftragen würden. Bevor
      ich die {rechnung_phrase} an Sie verschicke, wollte ich mir hiermit bestätigen
      lassen, dass Sie für {todesfall_phrase} beauftragt wurden.
    </p>
    {table_html}
    <p>Vielen Dank und freundliche Grüße<br>
       {cfg.get('COMPANY_NAME', '')}
    </p>
    """

    logger.info(
        "Starte Inquiry-E-Mail-Versand an %s für %s Aufträge",
        institut.email,
        anzahl,
    )

    msg = EmailMessage()
    msg["Subject"] = betreff
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = institut.email

    # Plaintext + HTML-Alternative
    msg.set_content(text_plain)
    msg.add_alternative(text_html, subtype="html")

    # --- SMTP-Versand ---
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception:
        logger.exception("Fehler beim SMTP-Versand der Inquiry-Mail")
        raise

    # --- IMAP: in 'Leichenschau/Anfragen' ablegen ---
    try:
        time.sleep(1)
        raw_message = msg.as_bytes()

        with imaplib.IMAP4_SSL(IMAP_SERVER) as imap:
            imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            imap.append(
                '"Leichenschau/Anfragen"',
                "\\Seen",
                imaplib.Time2Internaldate(time.localtime()),
                raw_message,
            )

        logger.info(
            "Inquiry-E-Mail im IMAP-Ordner 'Leichenschau/Anfragen' gespeichert (Institut %s).",
            institut.id,
        )
    except Exception:
        logger.exception("Fehler beim Speichern der Inquiry-Mail im IMAP-Ordner")
        # Versand war erfolgreich, Fehler hier nur loggen

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

            add_verlauf(auftrag, f"Rechnung Version {rechnung.version} erstellt")

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
    rechnungsdatum = date.today()
    year = str(rechnungsdatum.year)
    month = f"{rechnungsdatum.month:02d}"

    save_dir = Path(current_app.instance_path) / "invoices" / year / month
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
        return redirect(url_for("rechnungen.send_batch_email"))

    try:
        rechnung = create_rechnung_for_auftrag(auftrag)

        recipient, empfaenger_obj = determine_recipient_for_auftrag(auftrag)
        if not recipient:
            flash("Keine gültige E-Mail-Adresse gefunden.", "warning")
            return redirect(url_for("rechnungen.send_batch_email"))

        send_invoice_email(rechnung, recipient, empfaenger_obj=empfaenger_obj)

        # Optional: Status setzen – für später
        rechnung.status = RechnungsStatusEnum.SENT
        rechnung.gesendet_datum = datetime.now()
        auftrag.status = AuftragsStatusEnum.SENT
        add_verlauf(auftrag, f"Rechnung Version {rechnung.version} verschickt")

        db.session.commit()

        flash(
            f"Rechnung v{rechnung.version} für Auftrag #{auftrag.auftragsnummer or auftrag.id} an {recipient} gesendet.",
            "success",
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception("Fehler beim Einzelversand für auftrag_id=%s", auftrag.id)
        flash(f"Fehler beim Versenden der Rechnung: {exc}", "danger")

    return redirect(url_for("rechnungen.send_batch_email"))

@bp.route("/send-batch", methods=["GET", "POST"])
def send_batch_email():
    form = DummyCSRFForm()

    if request.method == "GET":
        sort = request.args.get("sort", "datum_asc")
        today = date.today()
        cutoff_date = today - timedelta(days=3)

        if sort == "datum_desc":
            order_by_clause = [desc(Auftrag.auftragsdatum), asc(Auftrag.id)]
        else:  # datum_asc
            order_by_clause = [asc(Auftrag.auftragsdatum), asc(Auftrag.id)]

        # OBEN: wirklich versandbereit (>= 3 Tage alt)
        auftraege_ready = (
            db.session.query(Auftrag)
            .filter(ready_for_email_filter())
            .order_by(*order_by_clause)
            .all()
        )

        # UNTEN: gleiche Kriterien, aber noch < 3 Tage alt
        auftraege_pending = (
            db.session.query(Auftrag)
            .filter(
                and_(
                    has_deliverable_email_filter(),
                    Auftrag.auftragsdatum > cutoff_date,   # noch nicht erfüllt
                )
            )
            .order_by(*order_by_clause)
            .all()
        )

        return render_template(
            "rechnungen/send_batch_select.html",
            auftraege=auftraege_ready,          # oben (bestehender Name)
            auftraege_pending=auftraege_pending, # unten
            today=today,
            cutoff_date=cutoff_date,
            sort=sort,
            form=form,
            timedelta=timedelta,
        )
    
    if not form.validate_on_submit():
        abort(400, description="Ungültiges CSRF-Token")

    # === POST: Auswahl wurde abgeschickt ===
    id_strings = request.form.getlist("auftrag_ids")  # Name wie im Template
    if not id_strings:
        flash("Sie haben keinen Auftrag ausgewählt.", "warning")
        return redirect(url_for("rechnungen.send_batch_email"))

    try:
        selected_ids = [int(x) for x in id_strings]
    except ValueError:
        flash("Ungültige Auswahl.", "danger")
        return redirect(url_for("rechnungen.send_batch_email"))

    # Nur die ausgewählten + weiterhin READY
    auftraege = (
        db.session.query(Auftrag)
        .filter(
            and_(
                Auftrag.id.in_(selected_ids),
                ready_for_email_filter(),
            )
        )
        .order_by(Auftrag.auftragsdatum.asc())
        .all()
    )

    successes: list[Auftrag] = []
    failures: list[tuple[Auftrag, str]] = []

    # Tracken, falls ausgewählte IDs nicht mehr READY / nicht gefunden sind
    found_ids = {a.id for a in auftraege}
    missing_ids = set(selected_ids) - found_ids
    if missing_ids:
        logger.warning(
            "send_batch_email: Einige ausgewählte Aufträge sind nicht mehr READY oder existieren nicht: %s",
            missing_ids,
        )

    for a in auftraege:
        try:
            rechnung = create_rechnung_for_auftrag(a)
            recipient, empfaenger_obj = determine_recipient_for_auftrag(a)

            if not recipient:
                failures.append((a, "Keine E-Mail-Adresse gefunden"))
                continue

            send_invoice_email(rechnung, recipient, empfaenger_obj=empfaenger_obj)

            rechnung.status = RechnungsStatusEnum.SENT
            rechnung.gesendet_datum = datetime.now()
            a.status = AuftragsStatusEnum.SENT
            add_verlauf(a, f"Rechnung Version {rechnung.version} verschickt")

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
        return redirect(url_for("rechnungen.send_batch_email"))

    return render_template(
        "rechnungen/send_batch_result.html",
        successes=successes,
        failures=failures,
    )

@bp.route("/inquiry", methods=["GET", "POST"])
def send_inquiry():
    form = DummyCSRFForm()

    if request.method == "GET":
        auftraege = (
            db.session.query(Auftrag)
            .filter(ready_for_inquiry_filter())
            .order_by(Auftrag.auftragsdatum.asc())
            .all()
        )
        return render_template(
            "rechnungen/inquiry_select.html",
            auftraege=auftraege,
            form=form,
        )

    # === POST: Anfrage für ein Institut senden ===
    if not form.validate_on_submit():
        abort(400, description="Ungültiges CSRF-Token")

    bestattungsinstitut_id = request.form.get("bestattungsinstitut_id", type=int)
    if not bestattungsinstitut_id:
        flash("Kein Bestattungsinstitut übermittelt.", "danger")
        return redirect(url_for("rechnungen.send_inquiry"))

    id_strings = request.form.getlist("auftrag_ids")
    if not id_strings:
        flash("Sie haben keine Aufträge ausgewählt.", "warning")
        return redirect(url_for("rechnungen.send_inquiry"))

    try:
        selected_ids = [int(x) for x in id_strings]
    except ValueError:
        flash("Ungültige Auswahl.", "danger")
        return redirect(url_for("rechnungen.send_inquiry"))

    # Aufträge holen, die noch im Status INQUIRY sind und zu diesem Institut gehören
    auftraege = (
        db.session.query(Auftrag)
        .filter(
            and_(
                Auftrag.id.in_(selected_ids),
                Auftrag.status == AuftragsStatusEnum.INQUIRY,
                Auftrag.kostenstelle == KostenstelleEnum.BESTATTUNGSINSTITUT,
                Auftrag.bestattungsinstitut_id == bestattungsinstitut_id,
            )
        )
        .order_by(Auftrag.auftragsdatum.asc())
        .all()
    )

    if not auftraege:
        flash("Keine passenden Aufträge für dieses Bestattungsinstitut gefunden.", "warning")
        return redirect(url_for("rechnungen.send_inquiry"))

    institut = auftraege[0].bestattungsinstitut
    if not institut or not institut.email:
        flash("Für das ausgewählte Bestattungsinstitut ist keine E-Mail hinterlegt.", "danger")
        return redirect(url_for("rechnungen.send_inquiry"))

    try:
        send_inquiry_email(institut, auftraege)

        for a in auftraege:
            institut = a.bestattungsinstitut 

            a.status = AuftragsStatusEnum.WAIT
            a.wait_due_date = date.today() + timedelta(days=7)
            a.is_inquired = True

            inst_name = (
                institut.kurzbezeichnung
                or institut.firmenname
                or f"Bestattungsinstitut #{institut.id}"
            )

            add_verlauf(
                a,
                (
                    f"Anfrage an {inst_name} gesendet, "
                    f"automatische Frist bis {a.wait_due_date.strftime('%d.%m.%Y')}"
                )
            )

        db.session.commit()
        flash(
            f"Anfrage für {len(auftraege)} Auftrag/Aufträge an {institut.email} gesendet.",
            "success",
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "Fehler beim Inquiry-Versand für Bestattungsinstitut_id=%s", bestattungsinstitut_id
        )
        flash(f"Fehler beim Versenden der Anfrage: {exc}", "danger")

    return redirect(url_for("rechnungen.send_inquiry"))

@bp.route("/send-batch-post", methods=["GET", "POST"])
def send_batch_post():
    """
    Postversand-Workflow:
    - GET: zeigt READY-Aufträge ohne zustellbare E-Mail (>= 3 Tage alt)
    - POST: erzeugt pro Auftrag eine neue Rechnung+PDF, setzt Status PRINT,
            packt PDFs als ZIP und liefert den Download zurück.
    """
    form = DummyCSRFForm()

    if request.method == "GET":
        sort = request.args.get("sort", "datum_asc")
        today = date.today()

        if sort == "datum_desc":
            order_by_clause = [desc(Auftrag.auftragsdatum), asc(Auftrag.id)]
        else:
            order_by_clause = [asc(Auftrag.auftragsdatum), asc(Auftrag.id)]

        auftraege_ready = (
            db.session.query(Auftrag)
            .options(selectinload(Auftrag.patient))
            .filter(ready_for_post_filter())
            .order_by(*order_by_clause)
            .all()
        )

        return render_template(
            "rechnungen/send_batch_post_select.html",
            auftraege=auftraege_ready,
            sort=sort,
            today=today,
            form=form,
        )
    
    # === POST ===
    if not form.validate_on_submit():
        abort(400, description="Ungültiges CSRF-Token")

    id_strings = request.form.getlist("auftrag_ids")
    if not id_strings:
        flash("Sie haben keinen Auftrag ausgewählt.", "warning")
        return redirect(url_for("rechnungen.send_batch_post"))

    try:
        selected_ids = [int(x) for x in id_strings]
    except ValueError:
        flash("Ungültige Auswahl.", "danger")
        return redirect(url_for("rechnungen.send_batch_post"))

    # Nur ausgewählte + weiterhin print-ready
    auftraege = (
        db.session.query(Auftrag)
        .options(selectinload(Auftrag.patient), selectinload(Auftrag.rechnungen))
        .filter(
            and_(
                Auftrag.id.in_(selected_ids),
                ready_for_post_filter(),
            )
        )
        .order_by(asc(Auftrag.auftragsdatum), asc(Auftrag.id))
        .all()
    )

    found_ids = {a.id for a in auftraege}
    missing_ids = set(selected_ids) - found_ids
    if missing_ids:
        logger.warning(
            "send_batch_post: Einige ausgewählte Aufträge sind nicht mehr READY/print-ready oder existieren nicht: %s",
            missing_ids,
        )

    successes: list[Auftrag] = []
    failures: list[tuple[Auftrag, str]] = []
    bundle_parts: list[Path] = []

    try:
        for a in auftraege:
            try:
                rechnung = create_rechnung_for_auftrag(a)

                # Status & Verlauf
                a.status = AuftragsStatusEnum.PRINT
                rechnung.status = RechnungsStatusEnum.CREATED
                add_verlauf(a, f"Rechnung v{rechnung.version} für Postversand erstellt")

                if not rechnung.pdf_path:
                    raise RuntimeError("pdf_path fehlt nach Rechnungserstellung")
                invoice_path = Path(rechnung.pdf_path)

                # >>> NEU: Anschreiben bei Angehörigen voranstellen
                if a.kostenstelle == KostenstelleEnum.ANGEHOERIGE:
                    empfaenger = pick_angehoeriger_for_auftrag(a)
                    cover_path = generate_anschreiben_pdf(rechnung)
                    bundle_parts.append(cover_path)

                bundle_parts.append(invoice_path)

                successes.append(a)

            except Exception as exc:
                logger.exception("send_batch_post: Fehler bei Auftrag %s", a.id)
                failures.append((a, str(exc)))

        db.session.commit()

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("send_batch_post: Fehler beim Commit")
        flash(f"Fehler beim Speichern des Postversand-Status: {exc}", "danger")
        return redirect(url_for("rechnungen.send_batch_post"))

    if not bundle_parts and failures:
        flash("Es konnten keine PDFs erzeugt werden.", "danger")
        return render_template(
            "rechnungen/send_batch_post_result.html",
            successes=successes,
            failures=failures,
        )

    bundle_dir = Path(current_app.instance_path) / "exports" / "postversand"
    bundle_name = f"Postversand_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    merge_pdfs(bundle_parts, bundle_dir / bundle_name)

    if failures:
        flash(f"{len(successes)} OK, {len(failures)} Fehler – Sammel-PDF enthält nur erfolgreiche.", "warning")

    flash("Sammel-PDF erstellt.", "success")

    # Statt direktem Download: Result-Page mit Download-Link
    return render_template(
        "rechnungen/send_batch_post_result.html",
        successes=successes,
        failures=failures,
        bundle_name=bundle_name,   # <-- nur Name übergeben
    )

@bp.route("/print/batch", methods=["GET", "POST"], endpoint="print_batch")
def print_batch():
    # 1) Datensatzbasis: alle PRINT-Aufträge
    auftraege = (
        db.session.query(Auftrag)
        .filter(Auftrag.status == AuftragsStatusEnum.PRINT)
        .order_by(Auftrag.id.asc())
        .all()
    )

    form = PrintBatchToSentForm()

    if request.method == "GET":
        # Default Versanddatum = heute
        # form.versanddatum.data = date.today()

        # Checkbox-Liste befüllen (alle vorausgewählt)
        form.items.entries = []  # sicherheitshalber
        for a in auftraege:
            form.items.append_entry({
                "auftrag_id": a.id,
                "checked": True,
            })

        return render_template("rechnungen/print_batch.html", form=form, auftraege=auftraege)

    # POST
    if form.validate_on_submit():
        versanddatum = form.versanddatum.data

        # Map auftrag_id -> checked aus dem Form
        selected_ids = [
            item.auftrag_id.data
            for item in form.items
            if item.checked.data
        ]

        if not selected_ids:
            flash("Keine Aufträge ausgewählt.", "warning")
            return redirect(url_for("rechnungen.print_batch"))

        # Aufträge laden (nur die ausgewählten + noch PRINT zur Sicherheit)
        selected_auftraege = (
            db.session.query(Auftrag)
            .filter(Auftrag.id.in_(selected_ids))
            .filter(Auftrag.status == AuftragsStatusEnum.PRINT)
            .all()
        )

        updated = 0
        for a in selected_auftraege:
            # Auftrag -> SENT
            a.status = AuftragsStatusEnum.SENT
            updated += 1

            # Zugehörige höchste Rechnung im Status CREATED -> SENT
            # "höchste" = z.B. max(version) oder max(id) – nimm das, was bei dir stimmt.
            inv = (
                db.session.query(Rechnung)
                .filter(Rechnung.auftrag_id == a.id)
                .filter(Rechnung.status == RechnungsStatusEnum.CREATED)
                .order_by(Rechnung.version.desc(), Rechnung.id.desc())  # falls version existiert
                .first()
            )
            if inv:
                inv.status = RechnungsStatusEnum.SENT

            # Verlauf (empfohlen)
            add_verlauf(
                auftrag=a,
                datum=versanddatum,
                text="Postalischer Versand",
            )

        db.session.commit()
        flash(f"{updated} Auftrag/Aufträge wurden auf SENT gesetzt.", "success")
        return redirect(url_for("rechnungen.print_batch")) 

    # Form invalid
    flash("Bitte Eingaben prüfen.", "danger")
    return render_template("rechnungen/print_batch.html", form=form, auftraege=auftraege)

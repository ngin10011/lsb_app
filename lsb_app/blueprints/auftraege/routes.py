# lsb_app/blueprints/auftraege/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from lsb_app.blueprints.auftraege import bp
from lsb_app.extensions import db
from lsb_app.models import (Auftrag, AuftragsStatusEnum,
        Bestattungsinstitut, Rechnung)
from lsb_app.forms import (AuftragForm, DummyCSRFForm,
        InstitutForm, InstitutSelectForm)
from lsb_app.models.adresse import Adresse
from lsb_app.services.auftrag_filters import ready_for_email_filter
from datetime import date, timedelta, datetime
from sqlalchemy import asc, desc, and_, or_, func
from sqlalchemy.orm import selectinload
from lsb_app.services.verlauf import add_verlauf

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
        auftrag.wait_due_date = form.wait_due_date.data if auftrag.status == AuftragsStatusEnum.WAIT else None
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

@bp.route("/ready-email")
def ready_email_list():
    # Sortier-Parameter aus der URL lesen, Default: ältestes Datum zuerst
    sort = request.args.get("sort", "datum_asc")

    if sort == "datum_desc":
        order_by_clause = [desc(Auftrag.auftragsdatum), asc(Auftrag.id)]
    elif sort == "kostenstelle_asc":
        order_by_clause = [asc(Auftrag.kostenstelle), asc(Auftrag.auftragsdatum)]
    elif sort == "kostenstelle_desc":
        order_by_clause = [desc(Auftrag.kostenstelle), asc(Auftrag.auftragsdatum)]
    else:  # "datum_asc" oder alles andere
        order_by_clause = [asc(Auftrag.auftragsdatum), asc(Auftrag.id)]

    auftraege = (
        db.session.query(Auftrag)
        .filter(ready_for_email_filter())
        .order_by(*order_by_clause)
        .all()
    )

    return render_template(
        "auftraege/ready_email.html",
        auftraege=auftraege,
        sort=sort,
    )


@bp.route("/wait", methods=["GET", "POST"])
def wait_list():
    """Übersicht aller Aufträge im Status WAIT, getrennt nach BI-Anfrage und sonstigen Fällen."""

    form = DummyCSRFForm()
    today = date.today()
    sort = request.args.get("sort", "due_asc")

    # === POST: ausgewählte BI-Anfrage-Aufträge auf READY setzen ===
    if request.method == "POST":
        if not form.validate_on_submit():
            abort(400, description="Ungültiges CSRF-Token")

        id_strings = request.form.getlist("auftrag_ids")
        if not id_strings:
            flash("Sie haben keinen Auftrag ausgewählt.", "warning")
            return redirect(url_for("auftraege.wait_list", sort=sort))

        try:
            ids = [int(x) for x in id_strings]
        except ValueError:
            flash("Ungültige Auswahl.", "danger")
            return redirect(url_for("auftraege.wait_list", sort=sort))

        auftraege = (
            db.session.query(Auftrag)
            .filter(
                and_(
                    Auftrag.id.in_(ids),
                    Auftrag.status == AuftragsStatusEnum.WAIT,
                    Auftrag.is_inquired.is_(True),
                )
            )
            .all()
        )

        if not auftraege:
            flash("Keine passenden Aufträge gefunden.", "warning")
            return redirect(url_for("auftraege.wait_list", sort=sort))

        for a in auftraege:
            a.status = AuftragsStatusEnum.READY
            a.wait_due_date = None
            a.is_inquired = False
            add_verlauf(
                a,
                "Rückmeldung vom Bestattungsinstitut: Auftrag als READY markiert."
            )

        try:
            db.session.commit()
            flash(
                f"{len(auftraege)} Auftrag/Aufträge auf READY gesetzt.",
                "success",
            )
        except Exception as exc:
            db.session.rollback()
            flash(f"Fehler beim Aktualisieren der Aufträge: {exc}", "danger")

        return redirect(url_for("auftraege.wait_list", sort=sort))

    # === GET: Liste anzeigen ===

    if sort == "due_desc":
        order_by_clause = [desc(Auftrag.wait_due_date), asc(Auftrag.id)]
    elif sort == "datum_asc":
        order_by_clause = [asc(Auftrag.auftragsdatum), asc(Auftrag.id)]
    elif sort == "datum_desc":
        order_by_clause = [desc(Auftrag.auftragsdatum), asc(Auftrag.id)]
    else:  # "due_asc" oder alles andere
        order_by_clause = [asc(Auftrag.wait_due_date), asc(Auftrag.id)]

    # BI-Anfragen: WAIT + is_inquired = True
    auftraege_inquired = (
        db.session.query(Auftrag)
        .filter(
            and_(
                Auftrag.status == AuftragsStatusEnum.WAIT,
                Auftrag.is_inquired.is_(True),
            )
        )
        .order_by(*order_by_clause)
        .all()
    )

    # sonstige WAIT-Fälle: WAIT + (is_inquired False oder None)
    auftraege_other = (
        db.session.query(Auftrag)
        .filter(
            and_(
                Auftrag.status == AuftragsStatusEnum.WAIT,
                or_(Auftrag.is_inquired.is_(False), Auftrag.is_inquired.is_(None)),
            )
        )
        .order_by(*order_by_clause)
        .all()
    )

    return render_template(
        "auftraege/wait.html",
        today=today,
        sort=sort,
        form=form,
        auftraege_inquired=auftraege_inquired,
        auftraege_other=auftraege_other,
    )

@bp.route("/<int:aid>/bestattungsinstitut", methods=["GET", "POST"])
def bestattungsinstitut(aid: int):
    auftrag = db.session.get(Auftrag, aid)
    if not auftrag:
        abort(404)

    next_url = request.args.get("next") or url_for("patients.overview")

    # Form 1: bestehendes auswählen
    select_form = InstitutSelectForm(prefix="sel")
    institute = Bestattungsinstitut.query.order_by(
        Bestattungsinstitut.kurzbezeichnung.asc()
    ).all()
    select_form.institut_id.choices = [(i.id, f"{i.kurzbezeichnung} – {i.firmenname}") for i in institute]

    # Form 2: neu anlegen (dein bestehender InstitutForm)
    new_form = InstitutForm(prefix="new")
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), Adresse.hausnummer.asc(), Adresse.ort.asc()
    ).all()
    new_form.adresse_id.choices = [(a.id, str(a)) for a in adressen]

    # Initialwerte für GET
    if request.method == "GET":
        if auftrag.bestattungsinstitut_id:
            select_form.institut_id.data = auftrag.bestattungsinstitut_id

    # POST: Welches Formular wurde abgeschickt?
    # (WTForms: per prefix + Submit-Button gut unterscheidbar)
    if select_form.submit_select.data and select_form.validate_on_submit():
        auftrag.bestattungsinstitut_id = select_form.institut_id.data
        try:
            db.session.commit()
            flash("Bestattungsinstitut wurde aktualisiert.", "success")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    if new_form.submit.data and new_form.validate_on_submit():
        inst = Bestattungsinstitut(
            kurzbezeichnung=new_form.kurzbezeichnung.data,
            firmenname=new_form.firmenname.data,
            email=new_form.email.data,
            bemerkung=new_form.bemerkung.data,
            anschreibbar=bool(new_form.anschreibbar.data),
            adresse_id=new_form.adresse_id.data,
            rechnungadress_modus=new_form.rechnungadress_modus.data,
        )

        db.session.add(inst)
        db.session.flush()  # inst.id verfügbar

        auftrag.bestattungsinstitut_id = inst.id

        try:
            db.session.commit()
            flash("Neues Bestattungsinstitut angelegt und zugeordnet.", "success")
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")

    return render_template(
        "auftraege/bestattungsinstitut.html",
        auftrag=auftrag,
        select_form=select_form,
        new_form=new_form,
        next_url=next_url,
    )

@bp.route("/overdue")
def overdue_list():
    now = datetime.now()
    cutoff = now - timedelta(days=30)

    latest_rechnung = (
        db.session.query(
            Rechnung.auftrag_id.label("auftrag_id"),
            func.max(Rechnung.version).label("max_version"),
        )
        .group_by(Rechnung.auftrag_id)
        .subquery()
    )

    rows = (
        db.session.query(Auftrag, Rechnung)
        .join(latest_rechnung, latest_rechnung.c.auftrag_id == Auftrag.id)
        .join(
            Rechnung,
            and_(
                Rechnung.auftrag_id == latest_rechnung.c.auftrag_id,
                Rechnung.version == latest_rechnung.c.max_version,
            ),
        )
        .options(selectinload(Auftrag.patient))
        .filter(Rechnung.gesendet_datum.isnot(None))
        .filter(Rechnung.gesendet_datum <= cutoff)
        .order_by(Rechnung.gesendet_datum.asc())
        .all()
    )

    items = []
    for auftrag, rechnung in rows:
        days_since_sent = (now - rechnung.gesendet_datum).days
        overdue_days = max(0, days_since_sent - 30)

        items.append(
            dict(
                auftrag=auftrag,
                rechnung=rechnung,
                days_since_sent=days_since_sent,
                overdue_days=overdue_days,
            )
        )

    return render_template("auftraege/overdue.html", items=items, cutoff=cutoff)
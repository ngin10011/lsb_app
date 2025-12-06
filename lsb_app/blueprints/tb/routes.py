# lsb_app/blueprints/tb/routes.py
from flask import render_template, redirect, url_for, request, jsonify, flash
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from lsb_app.forms import PatientForm, TBPatientForm
from lsb_app.services.address_validation import check_address_exists
import enum
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy import event, func, cast, Integer
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from lsb_app.extensions import db
from lsb_app.models import (Patient, GeschlechtEnum, Adresse, 
                    Auftrag, Verlauf, Angehoeriger,
                    Bestattungsinstitut, Behoerde,
                    AuftragsStatusEnum)
from faker import Faker
from datetime import date
from lsb_app.services.verlauf import add_verlauf
import random
import click
from lsb_app.blueprints.tb import bp
import logging
logger = logging.getLogger(__name__)

def _next_auftragsnummer():
    max_num = db.session.query(func.max(Auftrag.auftragsnummer)).scalar()
    return (max_num or 0) + 1

@bp.route("/test-log")
def test_log():
    logger.debug("🐛 DEBUG aus tb.routes")
    logger.info("ℹ️ INFO aus tb.routes")
    logger.error("❌ ERROR aus tb.routes")
    return "ok"

@bp.route("/api/validate_address", methods=["POST"])
def api_validate_address():
    """
    Live-Adressprüfung für AJAX-Requests.
    Erwartet JSON: {strasse, hausnummer, plz, ort}
    Antwort: {valid: bool, message: str | null}
    """
    data = request.get_json() or {}

    strasse    = data.get("strasse", "") or ""
    hausnummer = data.get("hausnummer", "") or ""
    plz        = data.get("plz", "") or ""
    ort        = data.get("ort", "") or ""

    if not (strasse and hausnummer and plz and ort):
        return jsonify({
            "valid": False,
            "message": "Bitte Straße, Hausnummer, PLZ und Ort vollständig eingeben."
        }), 200

    ok, msg = check_address_exists(strasse, hausnummer, plz, ort)

    # Live-Check: bei ok is None zeigen wir rot „Dienst nicht erreichbar“
    if ok is None:
        return jsonify({
            "valid": False,
            "message": msg or "Adressdienst aktuell nicht erreichbar."
        }), 200

    return jsonify({
        "valid": bool(ok),
        "message": msg or ("Adresse gültig." if ok else "Adresse ungültig.")
    }), 200

@bp.route("/new", methods=["GET", "POST"])
def new():
    logger.debug("TB.new aufgerufen, Methode=%s", request.method)
    form = TBPatientForm()

    # Adress-Choices (bestehende)
    adressen = Adresse.query.order_by(
        Adresse.strasse.asc(), 
        Adresse.hausnummer.asc(), 
        Adresse.ort.asc()
    ).all()
    form.meldeadresse_id.choices = [(-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]
    form.auftragsadresse_id.choices = [(-2, "🟰 Wie Meldeadresse"), (-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]

    # ➕ Bestattungsinstitut-Choices
    institute = Bestattungsinstitut.query.order_by(Bestattungsinstitut.kurzbezeichnung).all()
    form.bestattungsinstitut_id.choices = [
        (0, "— kein Bestattungsinstitut —"),
        (-1, "➕ Neues Bestattungsinstitut anlegen…"),
    ] + [(bi.id, f"{bi.kurzbezeichnung} – {bi.firmenname}") for bi in institute]

    form.bi_adresse_id.choices = [(-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]

    # Behörden-Choices (pro Subform):
    behoerden_all = Behoerde.query.order_by(Behoerde.name).all()
    for sub in form.behoerden:
        sub.form.sel_behoerde_id.choices = \
            [(0, "— keine Behörde —"), (-1, "➕ Neue Behörde anlegen…")] + [(b.id, b.name) for b in behoerden_all]
        sub.form.beh_adresse_id.choices = [(-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]

    if request.method == "GET":
        form.auftragsnummer.data = _next_auftragsnummer()
    
    if request.method == "POST" and "add_relative" in request.form:
        form.has_relatives.data = "some"
        logger.info("TB.new: weiterer Angehöriger angefordert")
        form.angehoerige.append_entry()
        # Choices für das neu angehängte Subform setzen:
        new = form.angehoerige[-1].form
        new.geschlecht.choices = [("", "— bitte wählen —")] + [(g.value, g.value) for g in GeschlechtEnum]
        new.adresse_choice.choices = [
            (0,  "— bitte wählen —"),
            (-2, "🟰 Wie Meldeadresse"),
            (-4, "🟰 Wie Auftragsadresse"),
            (-1, "➕ Neue Adresse anlegen…"),
            (-3, "Unbekannt"),
        ]
        return render_template("tb/new.html", form=form)
    
    if request.method == "POST" and ("add_relative" in request.form or "add_behoerde" in request.form):
        if not form.auftragsnummer.data:
            form.auftragsnummer.data = _next_auftragsnummer()
    
    if request.method == "POST" and "add_behoerde" in request.form:
        logger.info("TB.new: weitere Behörde angefordert")
        form.behoerden.append_entry()
        # Choices für das neu angehängte Subform setzen:
        sub = form.behoerden[-1].form
        sub.sel_behoerde_id.choices = \
            [(0, "— keine Behörde —"), (-1, "➕ Neue Behörde anlegen…")] + [(b.id, b.name) for b in behoerden_all]
        sub.beh_adresse_id.choices = [(-1, "➕ Neue Adresse anlegen…")] + [(a.id, str(a)) for a in adressen]
        return render_template("tb/new.html", form=form)


    if form.validate_on_submit():
        # --- Meldeadresse bestimmen (wie bisher) ---
        if form.meldeadresse_id.data != -1:
            adr_melde = Adresse.query.get(form.meldeadresse_id.data)
            if not adr_melde:
                logger.warning(
                    "TB.new: Meldeadresse mit ID %s nicht gefunden",
                    form.meldeadresse_id.data,
                )
                return render_template("tb/new.html", form=form, error="Meldeadresse nicht gefunden.")
        else:
            required = ["new_strasse", "new_hausnummer", "new_plz", "new_ort"]
            if any(not getattr(form, f).data for f in required):
                return render_template("tb/new.html", form=form, error="Bitte alle Felder der Meldeadresse ausfüllen.")
            
            # 🔍 Adressvalidierung (Meldeadresse)
            ok, msg = check_address_exists(
                form.new_strasse.data,
                form.new_hausnummer.data,
                form.new_plz.data,
                form.new_ort.data,
            )
            if ok is False:
                form.new_strasse.errors.append(msg)
                return render_template("tb/new.html", form=form)
            elif ok is None:
                flash(msg or "Adressdienst aktuell nicht erreichbar, Meldeadresse wurde ohne Prüfung übernommen.", "warning")

            
            adr_melde = Adresse.query.filter_by(
                strasse=form.new_strasse.data,
                hausnummer=form.new_hausnummer.data,
                plz=form.new_plz.data,
                ort=form.new_ort.data,
            ).first() or Adresse(
                strasse=form.new_strasse.data,
                hausnummer=form.new_hausnummer.data,
                plz=form.new_plz.data,
                ort=form.new_ort.data,
            )
            db.session.add(adr_melde); db.session.flush()

        # --- Auftragsadresse bestimmen ---
        sel = form.auftragsadresse_id.data
        if sel == -2:
            adr_auftrag = adr_melde
        elif sel == -1:
            required2 = ["auftrag_strasse", "auftrag_hausnummer", "auftrag_plz", "auftrag_ort"]
            if any(not getattr(form, f).data for f in required2):
                return render_template("tb/new.html", form=form, error="Bitte alle Felder der Auftragsadresse ausfüllen.")
            
            # 🔍 Adressvalidierung (Auftragsadresse)
            ok, msg = check_address_exists(
                form.auftrag_strasse.data,
                form.auftrag_hausnummer.data,
                form.auftrag_plz.data,
                form.auftrag_ort.data,
            )
            if ok is False:
                form.auftrag_strasse.errors.append(msg)
                return render_template("tb/new.html", form=form)
            elif ok is None:
                flash(msg or "Adressdienst aktuell nicht erreichbar, Auftragsadresse wurde ohne Prüfung übernommen.", "warning")

            
            adr_auftrag = Adresse.query.filter_by(
                strasse=form.auftrag_strasse.data,
                hausnummer=form.auftrag_hausnummer.data,
                plz=form.auftrag_plz.data,
                ort=form.auftrag_ort.data,
            ).first() or Adresse(
                strasse=form.auftrag_strasse.data,
                hausnummer=form.auftrag_hausnummer.data,
                plz=form.auftrag_plz.data,
                ort=form.auftrag_ort.data,
            )
            db.session.add(adr_auftrag); db.session.flush()
        else:
            adr_auftrag = Adresse.query.get(sel)
            if not adr_auftrag:
                logger.warning(
                    "TB.new: Auftragsadresse mit ID %s nicht gefunden",
                    sel,
                )
                return render_template("tb/new.html", form=form, error="Auftragsadresse nicht gefunden.")

        # --- Patient anlegen ---
        p = Patient()
        p.name         = form.name.data
        p.geburtsname  = form.geburtsname.data
        p.vorname      = form.vorname.data
        p.geburtsdatum = form.geburtsdatum.data
        p.geschlecht   = form.geschlecht.data
        p.meldeadresse = adr_melde
        db.session.add(p)

        # 3) Bestattungsinstitut bestimmen (optional)
        bi_sel = form.bestattungsinstitut_id.data
        bi_obj = None

        if bi_sel == 0:
            bi_obj = None
        elif bi_sel == -1:
            # Minimalpflichten prüfen: Kurzbezeichnung & Firmenname
            if not form.bi_kurz.data or not form.bi_firma.data:
                return render_template("tb/new.html", form=form, error="Bitte Kurzbezeichnung und Firmenname für das neue Bestattungsinstitut angeben.")

            # Adresse für das neue Institut bestimmen:
            if form.bi_adresse_id.data != -1:
                bi_addr = Adresse.query.get(form.bi_adresse_id.data)
                if not bi_addr:
                    return render_template("tb/new.html", form=form, error="Ausgewählte Institutsadresse nicht gefunden.")
            else:
                # Neue Adresse anlegen → alle Felder nötig
                req_bi_addr = [form.bi_strasse.data, form.bi_hausnummer.data, form.bi_plz.data, form.bi_ort.data]
                if any(not v for v in req_bi_addr):
                    return render_template("tb/new.html", form=form, error="Bitte alle Felder der neuen Institutsadresse ausfüllen.")
                
                # 🔍 Adressvalidierung (Bestattungsinstitut)
                ok, msg = check_address_exists(
                    form.bi_strasse.data,
                    form.bi_hausnummer.data,
                    form.bi_plz.data,
                    form.bi_ort.data,
                )
                if ok is False:
                    form.bi_strasse.errors.append(msg)
                    return render_template("tb/new.html", form=form)
                elif ok is None:
                    flash(msg or "Adressdienst aktuell nicht erreichbar, Institutsadresse wurde ohne Prüfung übernommen.", "warning")

                
                bi_addr = Adresse.query.filter_by(
                    strasse=form.bi_strasse.data,
                    hausnummer=form.bi_hausnummer.data,
                    plz=form.bi_plz.data,
                    ort=form.bi_ort.data,
                ).first() or Adresse(
                    strasse=form.bi_strasse.data,
                    hausnummer=form.bi_hausnummer.data,
                    plz=form.bi_plz.data,
                    ort=form.bi_ort.data,
                )
                db.session.add(bi_addr)
                db.session.flush()

            # Institut selbst
            bi_obj = Bestattungsinstitut(
                kurzbezeichnung=form.bi_kurz.data,
                firmenname=form.bi_firma.data,
                email=form.bi_email.data,
                bemerkung=form.bi_bemerkung.data,
                adresse=bi_addr,
            )
            db.session.add(bi_obj)
            db.session.flush()
        else:
            bi_obj = Bestattungsinstitut.query.get(bi_sel)
            if not bi_obj:
                logger.warning(
                    "TB.new: Bestattungsinstitut mit ID %s nicht gefunden",
                    bi_sel,
                )
                return render_template("tb/new.html", form=form, error="Bestattungsinstitut nicht gefunden.")

        # --- Auftrag anlegen ---
        a = Auftrag(
            auftragsnummer=form.auftragsnummer.data,
            auftragsdatum=form.auftragsdatum.data,
            auftragsuhrzeit=form.auftragsuhrzeit.data,
            kostenstelle=form.kostenstelle.data,
            mehraufwand=bool(form.mehraufwand.data),
            bemerkung=form.bemerkung.data,
            auftragsadresse=adr_auftrag,
            bestattungsinstitut=bi_obj,
            status=form.status.data,
            patient=p,
        )
        db.session.add(a) 

        # --- ersten Verlaufseintrag anlegen ---
        add_verlauf(a, f"TB-Auftrag angelegt", datum=date.today())

        # --- Mehrere Angehörige anlegen ---
        if form.has_relatives.data == "some":
            for sub in form.angehoerige.entries:
                f = sub.form
                any_person_field = any([
                    f.name.data, f.vorname.data, f.verwandtschaftsgrad.data,
                    f.telefonnummer.data, f.email.data
                ])
                if not any_person_field:
                    continue

                # Adresse je Angehöriger
                choice = f.adresse_choice.data
                if choice == -2:       # wie Melde
                    ang_addr = adr_melde
                elif choice == -4:     # wie Auftrag
                    ang_addr = adr_auftrag
                elif choice == -1:     # neu
                    # DEBUG: Werte anzeigen
                    logger.debug(
                        "Angehörigenadresse (raw): strasse=%r, hausnummer=%r, plz=%r, ort=%r",
                        f.strasse.data, f.hausnummer.data, f.plz.data, f.ort.data
                    )

                    req = [f.strasse.data, f.hausnummer.data, f.plz.data, f.ort.data]
                    if any(not v for v in req):
                        return render_template("tb/new.html", form=form, error="Bitte alle Felder der Angehörigenadresse ausfüllen.")
                    
                    # 🔍 Adressvalidierung (Angehörigenadresse)
                    ok, msg = check_address_exists(
                        f.strasse.data,
                        f.hausnummer.data,
                        f.plz.data,
                        f.ort.data,
                    )
                    if ok is False:
                        f.strasse.errors.append(msg)
                        return render_template("tb/new.html", form=form)
                    elif ok is None:
                        flash(msg or "Adressdienst aktuell nicht erreichbar, Angehörigenadresse wurde ohne Prüfung übernommen.", "warning")

                    
                    ang_addr = Adresse.query.filter_by(
                        strasse=f.strasse.data,
                        hausnummer=f.hausnummer.data,
                        plz=f.plz.data,
                        ort=f.ort.data,
                    ).first() or Adresse(
                        strasse=f.strasse.data,
                        hausnummer=f.hausnummer.data,
                        plz=f.plz.data,
                        ort=f.ort.data,
                    )
                    db.session.add(ang_addr); db.session.flush()
                else:                  # -3 = unbekannt
                    ang_addr = None

                ang = Angehoeriger(
                    name=f.name.data,
                    vorname=f.vorname.data,
                    geschlecht=f.geschlecht.data or GeschlechtEnum.UNBEKANNT,
                    verwandtschaftsgrad=f.verwandtschaftsgrad.data,
                    telefonnummer=f.telefonnummer.data,
                    email=f.email.data,
                    adresse=ang_addr,
                    patient=p,
                )
                db.session.add(ang)

        # ▼ Mehrere Behörden
        for sub in form.behoerden.entries:
            f = sub.form
            sel_id = f.sel_behoerde_id.data
            if sel_id == 0:
                continue  # keine Behörde für diesen Eintrag

            if sel_id > 0:
                b = Behoerde.query.get(sel_id)
                if b:
                    a.behoerden.append(b)
                continue

            # Neuanlage:
            if not f.name.data:
                return render_template("tb/new.html", form=form, error="Bitte Namen der neuen Behörde angeben.")

            # Adresse bestimmen
            if f.beh_adresse_id.data != -1:
                beh_addr = Adresse.query.get(f.beh_adresse_id.data)
                if not beh_addr:
                    return render_template("tb/new.html", form=form, error="Ausgewählte Behördenadresse nicht gefunden.")
            else:
                req = [f.beh_strasse.data, f.beh_hausnummer.data, f.beh_plz.data, f.beh_ort.data]
                if any(not v for v in req):
                    return render_template("tb/new.html", form=form, error="Bitte alle Felder der neuen Behördenadresse ausfüllen.")
                
                # 🔍 Adressvalidierung (Behördenadresse)
                ok, msg = check_address_exists(
                    f.beh_strasse.data,
                    f.beh_hausnummer.data,
                    f.beh_plz.data,
                    f.beh_ort.data,
                )
                if ok is False:
                    f.beh_strasse.errors.append(msg)
                    return render_template("tb/new.html", form=form)
                elif ok is None:
                    flash(msg or "Adressdienst aktuell nicht erreichbar, Behördenadresse wurde ohne Prüfung übernommen.", "warning")

                
                beh_addr = Adresse.query.filter_by(
                    strasse=f.beh_strasse.data,
                    hausnummer=f.beh_hausnummer.data,
                    plz=f.beh_plz.data,
                    ort=f.beh_ort.data,
                ).first() or Adresse(
                    strasse=f.beh_strasse.data,
                    hausnummer=f.beh_hausnummer.data,
                    plz=f.beh_plz.data,
                    ort=f.beh_ort.data,
                )
                db.session.add(beh_addr); db.session.flush()

            b_new = Behoerde(
                name=f.name.data,
                email=f.email.data,
                bemerkung=f.bemerkung.data,
                adresse=beh_addr,
            )
            db.session.add(b_new); db.session.flush()
            a.behoerden.append(b_new)

        try:
            logger.info(
                "TB.new: bereit zum Commit – Patient neu, geschlecht=%s; Auftrag auftragsnummer=%s, kostenstelle=%s; "
                "%d Angehörige, %d Behörden",
                p.geschlecht.name if p.geschlecht else None,
                a.auftragsnummer,
                a.kostenstelle.name if a.kostenstelle else None,
                len(form.angehoerige.entries),
                len(form.behoerden.entries),
            )
            db.session.commit()
            flash("TB gespeichert.", "success")
            logger.info(
                "TB.new: Commit erfolgreich – patient_id=%s, auftrag_id=%s",
                p.id,
                a.id,
            )
        except IntegrityError:
            db.session.rollback()
            logger.warning(
                "TB.new: IntegrityError bei Commit – vermutlich doppelte Auftragsnummer %s",
                form.auftragsnummer.data,
            )
            form.auftragsnummer.errors.append("Auftragsnummer bereits vergeben.")
            return render_template("tb/new.html", form=form)

        logger.info("TB.new: Datensatz erfolgreich angelegt, Redirect auf patients.overview")
        return redirect(url_for("patients.overview"))

    # GET oder Validierungsfehler
    return render_template("tb/new.html", form=form)
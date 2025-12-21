# lsb_app/blueprints/zahlungen/routes.py
from __future__ import annotations

from flask import render_template, redirect, url_for, flash, request, abort
from lsb_app.blueprints.zahlungen import bp
from lsb_app.extensions import db
from lsb_app.forms.zahlung import ZahlungEingangForm
from lsb_app.models import Auftrag, Rechnung, RechnungsStatusEnum
from lsb_app.services.zahlungen import verbuche_zahlung

from sqlalchemy import desc
from decimal import Decimal


def _auftrag_or_404(aid: int) -> Auftrag:
    return db.session.get(Auftrag, aid) or abort(404)

def _aid_from_auftragsnummer(nr_raw: str) -> int | None:
    try:
        nr = int(str(nr_raw).strip())
    except (TypeError, ValueError):
        return None

    return (
        db.session.query(Auftrag.id)
        .filter(Auftrag.auftragsnummer == nr)
        .scalar()
    )


@bp.route("/new", methods=["GET", "POST"], endpoint="new")
@bp.route("/new/<int:aid>", methods=["GET", "POST"], endpoint="new_with_aid")
def new(aid: int | None = None):
    auftrag = _auftrag_or_404(aid) if aid is not None else None

    form = ZahlungEingangForm()

    # Prefill nur bei GET und wenn Kontext vorhanden
    if request.method == "GET" and auftrag:
        form.auftragsnummer.data = getattr(auftrag, "auftragsnummer", "") or ""

        # Betrag aus der neuesten SENT-Rechnung holen
        sent_rechnung = (
            db.session.query(Rechnung)
            .filter(
                Rechnung.auftrag_id == auftrag.id,
                Rechnung.status == RechnungsStatusEnum.SENT,
            )
            # "neueste" definieren – bei dir passt version perfekt
            .order_by(Rechnung.version.desc())
            .first()
        )

        if sent_rechnung:
            # WTForms DecimalField erwartet Decimal
            form.betrag.data = Decimal(sent_rechnung.betrag)

    if form.validate_on_submit():
        # aid sicher bestimmen (aus URL oder aus Auftragsnummer)
        resolved_aid = aid
        if resolved_aid is None:
            resolved_aid = _aid_from_auftragsnummer(form.auftragsnummer.data)

        if resolved_aid is None:
            flash("Auftragsnummer nicht gefunden oder ungültig.", "danger")
            return render_template("zahlungen/new.html", form=form, auftrag=auftrag)

        try:
            result = verbuche_zahlung(
                aid=resolved_aid,
                betrag=form.betrag.data,
                eingangsdatum=form.eingangsdatum.data,
                payee=form.payee.data,
            )
            flash(f"Zahlung verbucht: Auftrag #{result.auftrag_id} ist jetzt DONE.", "success")

            # Redirect: zurück zum Patienten wenn möglich, sonst Home
            if result.patient_id:
                return redirect(url_for("patients.detail", pid=result.patient_id))
            return redirect(url_for("home.index"))

        except ValueError as e:
            flash(str(e), "danger")

    return render_template("zahlungen/new.html", form=form, auftrag=auftrag)

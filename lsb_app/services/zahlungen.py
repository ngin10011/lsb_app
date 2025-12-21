# lsb_app/services/zahlungen.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from sqlalchemy import func, and_

from lsb_app.extensions import db
from lsb_app.models import Auftrag, Rechnung, AuftragsStatusEnum, RechnungsStatusEnum
from lsb_app.services.verlauf import add_verlauf
from lsb_app.services.ynab import create_transaction_leichenschau


@dataclass(frozen=True)
class ZahlungResult:
    auftrag_id: int
    patient_id: int | None
    ok_ynab: bool
    message_ynab: str


def _latest_rechnung_for_auftrag(aid: int) -> Rechnung | None:
    latest_sq = (
        db.session.query(
            Rechnung.auftrag_id.label("auftrag_id"),
            func.max(Rechnung.version).label("max_version"),
        )
        .filter(Rechnung.auftrag_id == aid)
        .group_by(Rechnung.auftrag_id)
        .subquery()
    )

    return (
        db.session.query(Rechnung)
        .join(
            latest_sq,
            and_(
                latest_sq.c.auftrag_id == Rechnung.auftrag_id,
                latest_sq.c.max_version == Rechnung.version,
            ),
        )
        .first()
    )


def verbuche_zahlung(*, aid: int, betrag: Decimal, eingangsdatum: date, payee: str) -> ZahlungResult:
    if betrag is None or betrag < 0:
        raise ValueError("Betrag ist ungültig.")
    if not eingangsdatum:
        raise ValueError("Eingangsdatum fehlt.")
    if not payee or not payee.strip():
        raise ValueError("Name fehlt.")

    auftrag = db.session.get(Auftrag, aid)
    if not auftrag:
        raise ValueError(f"Auftrag nicht gefunden: #{aid}")

    if auftrag.status == AuftragsStatusEnum.DONE:
        raise ValueError("Auftrag ist bereits DONE.")

    rechnung = _latest_rechnung_for_auftrag(aid)

    # Auftrag DONE
    auftrag.status = AuftragsStatusEnum.DONE

    # optional: Rechnung PAID
    if rechnung:
        rechnung.status = RechnungsStatusEnum.PAID

    add_verlauf(
        auftrag=auftrag,
        text=f"Zahlungseingang quittiert: {betrag} € am {eingangsdatum.strftime("%d.%m.%Y")} von {payee.strip()}.",
    )

    db.session.commit()

    # payee = "Testbezahler"
    # amount_total = 100.00
    invoice = []
    invoice.append(str(auftrag.auftragsnummer))
    # date_transaction = "2025-12-21"

    ok, msg = create_transaction_leichenschau(
        payee=payee,
        amount_total=betrag,
        invoice=invoice,
        date_transaction=eingangsdatum.isoformat(),
    )

    return ZahlungResult(
        auftrag_id=auftrag.id, 
        patient_id=getattr(auftrag, "patient_id", None),
        ok_ynab=ok,
        message_ynab=msg,
        )

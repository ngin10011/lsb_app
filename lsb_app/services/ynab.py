# lsb_app/services/ynab.py
from __future__ import annotations

from decimal import Decimal, getcontext, ROUND_HALF_UP
import logging
from flask import current_app

from lsb_app.clients.ynab_client import YnabClient, YnabClientConfig, YnabApiError

logger = logging.getLogger(__name__)
getcontext().prec = 10


def _runde(zahl: Decimal) -> Decimal:
    return zahl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def berechne_abgaben(betrag_raw: str | float | Decimal) -> dict[str, Decimal]:
    try:
        betrag = Decimal(str(betrag_raw).replace(",", "."))
    except Exception as e:
        raise ValueError("Ungültiger Betrag") from e

    steuer = _runde(betrag * Decimal("0.40"))
    aerzteversorgung = _runde(betrag * Decimal("0.186"))
    aerztekammer = _runde(betrag * Decimal("0.0045"))
    ready_to_assign = betrag - (steuer + aerzteversorgung + aerztekammer)

    return {
        "betrag": _runde(betrag),
        "steuer": steuer,
        "aerzteversorgung": aerzteversorgung,
        "aerztekammer": aerztekammer,
        "ready": _runde(ready_to_assign),
    }


def _to_milliunits(eur: Decimal) -> int:
    # YNAB: 1 EUR = 1000 milliunits
    return int(_runde(eur) * 1000)


def get_ynab_client() -> YnabClient:
    """
    Factory: Tokens erst im App/Request-Kontext aus current_app lesen.
    => Kein "Working outside of application context" beim Import.
    """
    cfg = YnabClientConfig(
        access_token=current_app.config.get("YNAB_ACCESS_TOKEN", ""),
        budget_id=current_app.config.get("YNAB_BUDGET_ID", ""),
    )
    return YnabClient(cfg)


def get_account_map() -> dict[str, str]:
    client = get_ynab_client()
    accounts = client.list_accounts()
    return {a["name"]: a["id"] for a in accounts}


def get_category_map() -> dict[str, str]:
    client = get_ynab_client()
    cats = client.list_categories()
    return {c["name"]: c["id"] for c in cats}


def create_transaction_leichenschau(
    *,
    payee: str,
    amount_total: str | float | Decimal,
    invoice: list[str],
    date_transaction: str,
) -> tuple[bool, str]:
    """
    Fachlogik:
    - memo zusammenbauen
    - Abgaben berechnen
    - Subtransactions bauen
    - via YnabClient posten
    """

    # TODO: schöner: per config oder Mapping statt hardcodiert
    account_id = "7be5fc7c-6bc0-4e1e-9584-fb2f3c93493c"
    category_id_ready = "ee5de694-16d6-4648-8231-9b60e8bb0e3e"
    category_id_steuer = "443506bf-b0b1-4f62-8e9a-b7a921f581c6" # 2026
    category_id_aerzteversorgung = "43c90e0a-885f-4bcf-9583-3ded8429c564" # 2026
    category_id_aerztekammer = "71939d2c-8d40-4ada-9340-d465993701b5" # 2026
    # category_id_steuer = "a8eaf507-3ea8-4ced-bebe-c52cd9d90447" # 2025
    # category_id_aerzteversorgung = "bbec5758-1de3-44ff-b9c7-13220b8a964e" # 2025
    # category_id_aerztekammer = "8227ac8f-9634-4a29-8989-c57584f2060b" # 2025
    

    inv_clean = [i for i in invoice if i]  # leere Strings raus
    memo = "Leichenschau" if not inv_clean else "Leichenschau " + " + ".join(inv_clean)

    werte = berechne_abgaben(amount_total)

    payload = {
        "transaction": {
            "account_id": account_id,
            "date": date_transaction,
            "amount": _to_milliunits(werte["betrag"]),
            "payee_name": payee,
            "memo": memo,
            "cleared": "cleared",
            "approved": True,
            "subtransactions": [
                {"amount": _to_milliunits(werte["steuer"]), "category_id": category_id_steuer},
                {"amount": _to_milliunits(werte["aerzteversorgung"]), "category_id": category_id_aerzteversorgung},
                {"amount": _to_milliunits(werte["aerztekammer"]), "category_id": category_id_aerztekammer},
                {"amount": _to_milliunits(werte["ready"]), "category_id": category_id_ready},
            ],
        }
    }

    client = get_ynab_client()

    try:
        client.create_transaction(payload)
        text = f"✅ YNAB: {payee}, {werte['betrag']} €, Rechnung {inv_clean or '—'}"
        logger.info(text)
        return True, text
    except YnabApiError as e:
        text = f"❌ YNAB Fehler: {e}"
        logger.error(text)
        return False, text


def get_transactions_by_account(account_id: str, since_date: str | None = None) -> list[dict]:
    client = get_ynab_client()
    try:
        return client.list_transactions_by_account(account_id=account_id, since_date=since_date)
    except YnabApiError as e:
        logger.error("YNAB get_transactions failed: %s", e)
        return []

# lsb_app/clients/ynab_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import logging
import requests

logger = logging.getLogger(__name__)


class YnabApiError(RuntimeError):
    """Generischer Fehler für YNAB-API-Probleme."""
    pass


@dataclass(frozen=True)
class YnabClientConfig:
    access_token: str
    budget_id: str
    base_url: str = "https://api.ynab.com/v1"
    timeout: int = 20


class YnabClient:
    def __init__(self, cfg: YnabClientConfig):
        if not cfg.access_token:
            raise ValueError("YNAB access_token fehlt (YNAB_ACCESS_TOKEN).")
        if not cfg.budget_id:
            raise ValueError("YNAB budget_id fehlt (YNAB_BUDGET_ID).")
        self.cfg = cfg

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cfg.access_token}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.cfg.base_url}{path}"

    def _raise_for_status(self, r: requests.Response, msg: str) -> None:
        if r.status_code >= 400:
            raise YnabApiError(f"{msg}: {r.status_code} – {r.text}")

    def get_user(self) -> dict[str, Any]:
        r = requests.get(self._url("/user"), headers=self._headers(), timeout=self.cfg.timeout)
        self._raise_for_status(r, "YNAB get_user failed")
        return r.json()

    def list_accounts(self) -> list[dict[str, Any]]:
        r = requests.get(
            self._url(f"/budgets/{self.cfg.budget_id}/accounts"),
            headers=self._headers(),
            timeout=self.cfg.timeout,
        )
        self._raise_for_status(r, "YNAB list_accounts failed")
        return r.json()["data"]["accounts"]

    def list_categories(self) -> list[dict[str, Any]]:
        """
        Gibt die flache Liste der Kategorien zurück (ohne Gruppen),
        also response["data"]["category_groups"][*]["categories"][*]
        """
        r = requests.get(
            self._url(f"/budgets/{self.cfg.budget_id}/categories"),
            headers=self._headers(),
            timeout=self.cfg.timeout,
        )
        self._raise_for_status(r, "YNAB list_categories failed")

        data = r.json()["data"]["category_groups"]
        cats: list[dict[str, Any]] = []
        for g in data:
            cats.extend(g.get("categories", []))
        return cats

    def create_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload entspricht YNAB API: {"transaction": {...}}
        """
        r = requests.post(
            self._url(f"/budgets/{self.cfg.budget_id}/transactions"),
            headers=self._headers(),
            json=payload,
            timeout=self.cfg.timeout,
        )
        # YNAB: 201 Created bei Erfolg
        if r.status_code != 201:
            raise YnabApiError(f"YNAB create_transaction failed: {r.status_code} – {r.text}")
        return r.json()

    def list_transactions_by_account(self, *, account_id: str, since_date: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date

        r = requests.get(
            self._url(f"/budgets/{self.cfg.budget_id}/accounts/{account_id}/transactions"),
            headers=self._headers(),
            params=params,
            timeout=self.cfg.timeout,
        )
        self._raise_for_status(r, "YNAB list_transactions_by_account failed")
        return r.json()["data"]["transactions"]

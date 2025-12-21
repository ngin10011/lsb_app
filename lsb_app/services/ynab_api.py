# lsb_app/services/ynab_api.py
# from dotenv import load_dotenv
from flask import current_app
import os
import requests
import json
from datetime import date
import logging
# from beitragsberechnung import berechne_abgaben
from decimal import Decimal, getcontext, ROUND_HALF_UP


access_token = current_app.config["YNAB_ACCESS_TOKEN"]
budget_id = current_app.config["YNAB_BUDGET_ID"]

getcontext().prec = 10

def berechne_abgaben(betrag_raw: str):
    try:
        betrag = Decimal(betrag_raw.replace(",", "."))
    except Exception:
        raise ValueError("Ungültiger Betrag")
    
    def runde(zahl):
        return zahl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    steuer = runde(betrag * Decimal("0.40"))
    aerzteversorgung = runde(betrag * Decimal("0.186"))
    aerztekammer = runde(betrag * Decimal("0.0045"))

    ready_to_assign = betrag - (steuer + aerzteversorgung + aerztekammer)

    return {
        "betrag": runde(betrag),
        "steuer": steuer,
        "aerzteversorgung": aerzteversorgung,
        "aerztekammer": aerztekammer,
        "ready": runde(ready_to_assign)
    }

# load_dotenv()
# access_token = os.getenv("YNAB_ACCESS_TOKEN")

"""

script_dir = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(script_dir, "ynab.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

"""

# budget_id = "079cb31b-97ed-4d07-9958-03831bc5a373"

def get_user_info():
    headers = {
        "Authorization": f"Bearer {access_token}"
    }


    url = "https://api.ynab.com/v1/user"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("✅ Benutzerinformationen:")
        print(response.json())
    else:
        print(f"❌ Fehler: {response.status_code}")
        print(response.text)

def get_account_list():
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/accounts"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        account_map = {a["name"]: a["id"] for a in response_data["data"]["accounts"]}
        for name, id in account_map.items():
            print(f"{name} → {id}")
        
        return account_map
    else:
        print(f"❌ Fehler: {response.status_code}")
        print(response.text)

def get_categories_list():
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/categories"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()

        # output_path = os.path.join(script_dir, "output.json")

        # with open(output_path, "w", encoding="utf-8") as f:
        #     json.dump(response_data, f, indent=2, ensure_ascii=False)

        # print(json.dumps(response_data, indent=2))

        # Kategorien aus allen Gruppen extrahieren
        category_map = {
            cat["name"]: cat["id"]
            for group in response_data["data"]["category_groups"]
            for cat in group["categories"]
        }

        # Optional: anzeigen
        for name, cat_id in category_map.items():
            print(f"{name} → {cat_id}")

    else:
        print(f"❌ Fehler: {response.status_code}")
        print(response.text)

def create_test_transaction():

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/transactions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


    transaction_data = {
        "transaction": {
            "account_id": "eb8c520c-3088-4691-be08-f156d8ada196", # Deutsche Bank
            "date": date.today().isoformat(),
            "amount": 75000,  # 75.00 Euro = 75000 Milliunits
            "payee_name": "Max Mustermann",
            "memo": "Test 1234",
            "category_id": "fc293f51-d466-4e70-b003-4010094cc998", # Temp (uncat. yet)
            "cleared": "cleared",
            "approved": True
        }
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(transaction_data)
    )

    if response.status_code == 201:
        print("✅ Transaktion erfolgreich erstellt:")
        print(response.json())
    else:
        print(f"❌ Fehler: {response.status_code}")
        print(response.text)

def create_test_transaction_with_subtransactions(account_id):

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/transactions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


    transaction_data = {
        "transaction": {
            "account_id": f"{account_id}",
            "date": date.today().isoformat(),
            "amount": 75000,  # 75.00 Euro = 75000 Milliunits
            "payee_name": "Max Mustermann",
            "memo": "Test 1234",
            "cleared": "cleared",
            "approved": True,
            "subtransactions": [
                {
                    "amount": 25000, # 25.00 Euro
                    "category_id": "1928d6d3-56b7-449e-b421-522d54b6b0c2"
                },
                {
                    "amount": 50000,
                    "category_id": "00025d54-1479-4238-9a82-cb4c1cabbab5"
                }
            ]
        }
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(transaction_data)
    )

    if response.status_code == 201:
        print("✅ Transaktion erfolgreich erstellt:")
        print(response.json())
    else:
        print(f"❌ Fehler: {response.status_code}")
        print(response.text)

def create_transaction_leichenschau(
        account_id: str, payee: str, amount_total: str, 
        invoice: str, date_transaction: str
        ) -> tuple[bool, str]:

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/transactions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    werte = berechne_abgaben(amount_total)

    # In Milliunits umwandeln
    betrag_milli           = int(werte['betrag']           * 1000)
    steuer_milli           = int(werte['steuer']           * 1000)
    aerzteversorgung_milli = int(werte['aerzteversorgung'] * 1000)
    aerztekammer_milli     = int(werte['aerztekammer']     * 1000)
    ready_milli            = int(werte['ready']            * 1000)

    # Ausgabe zur Kontrolle
    # print("Betrag:", betrag_milli)
    # print("Steuer:", steuer_milli)
    # print("Ärzteversorgung:", aerzteversorgung_milli)
    # print("Ärztekammer:", aerztekammer_milli)
    # print("Ready to Assign:", ready_milli)


    transaction_data = {
        "transaction": {
            "account_id": account_id,
            "date": date_transaction,
            "amount": betrag_milli,
            "payee_name": payee,
            "memo": f"Leichenschau {invoice}",
            "cleared": "cleared",
            "approved": True,
            "subtransactions": [
                {
                    "amount": steuer_milli,
                    "category_id": "a8eaf507-3ea8-4ced-bebe-c52cd9d90447" # LS Steuer '25
                },
                {
                    "amount": aerzteversorgung_milli,
                    "category_id": "bbec5758-1de3-44ff-b9c7-13220b8a964e" # LS Ärzteversorgung '25
                },
                                {
                    "amount": aerztekammer_milli,
                    "category_id": "8227ac8f-9634-4a29-8989-c57584f2060b" # Bayr. Ärztekammer '25 [year]
                },
                                {
                    "amount": ready_milli,
                    "category_id": "ee5de694-16d6-4648-8231-9b60e8bb0e3e" # Inflow: Ready to Assign
                }
            ]
        }
    }

def create_transaction_leichenschau_v02(
        account_id: str, payee: str, amount_total: str, 
        invoice: list, date_transaction: str
        ) -> tuple[bool, str]:

    url = f"https://api.ynab.com/v1/budgets/{budget_id}/transactions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # memo = ""


    #TODO leere Rechnungsnummer abdecken!

    memo = "Leichenschau " + " + ".join(invoice)

    # if len(invoice) == 1:
    #     memo = f"Leichenschau {invoice[0]}"
    # elif len(invoice) > 1:
    #     memo = f"Leichenschau {invoice[0]}"
    #     for i in range(1, len(invoice) - 1):
    #         memo = memo + f" + {invoice[i]}"


    werte = berechne_abgaben(amount_total)

    # In Milliunits umwandeln
    betrag_milli           = int(werte['betrag']           * 1000)
    steuer_milli           = int(werte['steuer']           * 1000)
    aerzteversorgung_milli = int(werte['aerzteversorgung'] * 1000)
    aerztekammer_milli     = int(werte['aerztekammer']     * 1000)
    ready_milli            = int(werte['ready']            * 1000)

    # Ausgabe zur Kontrolle
    # print("Betrag:", betrag_milli)
    # print("Steuer:", steuer_milli)
    # print("Ärzteversorgung:", aerzteversorgung_milli)
    # print("Ärztekammer:", aerztekammer_milli)
    # print("Ready to Assign:", ready_milli)


    transaction_data = {
        "transaction": {
            "account_id": account_id,
            "date": date_transaction,
            "amount": betrag_milli,
            "payee_name": payee,
            "memo": memo,
            "cleared": "cleared",
            "approved": True,
            "subtransactions": [
                {
                    "amount": steuer_milli,
                    "category_id": "a8eaf507-3ea8-4ced-bebe-c52cd9d90447" # LS Steuer '25
                },
                {
                    "amount": aerzteversorgung_milli,
                    "category_id": "bbec5758-1de3-44ff-b9c7-13220b8a964e" # LS Ärzteversorgung '25
                },
                                {
                    "amount": aerztekammer_milli,
                    "category_id": "8227ac8f-9634-4a29-8989-c57584f2060b" # Bayr. Ärztekammer '25 [year]
                },
                                {
                    "amount": ready_milli,
                    "category_id": "ee5de694-16d6-4648-8231-9b60e8bb0e3e" # Inflow: Ready to Assign
                }
            ]
        }
    }

    # print(transaction_data)
    logger.info(f"Transaction Data: {transaction_data}")

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(transaction_data)
    )

    if response.status_code == 201:
        text = f"✅ Transaktion erfolgreich erstellt: {payee}, {betrag_milli/1000:.2f} €, Rechnung {invoice}"
        logger.info(text)
        # print("✅ Transaktion erfolgreich erstellt:")
        # print(response.json())
        return True, text
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 1))
        text = f"⏳ Rate Limit erreicht (429). Bitte {retry_after} Sekunden warten."
        logger.warning(text)
        return False, text
    else:
        text = f"❌ Fehler: {response.status_code}"
        logger.error(f"{text}: {response.text.strip()}")
        # print(f"❌ Fehler: {response.status_code}")
        # print(response.text)
        return False, text

def get_transactions_by_account(account_id: str, since_date: str | None = None) -> list[dict]:
    """
    Ruft alle Transaktionen eines bestimmten Kontos ab, optional ab einem bestimmten Datum,
    und filtert dabei 'uncleared' (pending) Transaktionen heraus.
    """
    url = f"https://api.ynab.com/v1/budgets/{budget_id}/accounts/{account_id}/transactions"
    headers = {"Authorization": f"Bearer {access_token}"}

    params = {}
    if since_date:
        params["since_date"] = since_date  # YYYY-MM-DD Format

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        tx_list = response.json()["data"]["transactions"]
        # cleared_tx = [tx for tx in tx_list if tx.get("cleared") != "uncleared"]
        # logger.info(f"{len(cleared_tx)} Transaktionen abgerufen (ohne pending).")
        # return cleared_tx
        return tx_list
    else:
        error_msg = f"Fehler beim Abruf: {response.status_code} – {response.text}"
        logger.error(error_msg)
        return []

if __name__ == "__main__":
    accounts = get_account_list()
    db_account_id = accounts.get("N26")
    if db_account_id:
        txs = get_transactions_by_account(db_account_id, since_date="2025-07-01")
        for t in txs:
            # print(f"{t['date']} | {t['payee_name']} | {t['amount']/1000:.2f} € | {t['cleared']}")
            print("-----------------")
            print(json.dumps(t, indent=2, ensure_ascii=False))
            # print(t)


# get_user_info()

# create_test_transaction()
# get_categories_list()

# account_id = "eb8c520c-3088-4691-be08-f156d8ada196" # Deutsche Bank
# accounts = get_account_list()
# account_id = accounts["Deutsche Bank"]
# create_test_transaction_with_subtransactions(account_id=account_id)


# accounts = get_account_list()
# account_id = accounts["Deutsche Bank"]
# payee = "Max Mustermann"
# amount_total = "100.00"
# invoice = "0001"
# date_transaction = "2025-07-07"

# create_transaction_leichenschau(
#     account_id=account_id, payee=payee, amount_total=amount_total, 
#     invoice=invoice, date_transaction=date_transaction
#     )

# solution = berechne_abgaben("100.00")
# print(solution)
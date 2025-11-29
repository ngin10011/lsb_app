import requests
from flask import current_app

def check_address_exists(strasse, hausnummer, plz, ort):
    url = current_app.config["NOMINATIM_URL"]
    ua  = current_app.config["NOMINATIM_USER_AGENT"]

    params = {
        "q": f"{strasse} {hausnummer} {plz} {ort}",
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
    }
    headers = {"User-Agent": ua}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception:
        return False, "Adressdienst nicht erreichbar."

    results = resp.json()
    if not results:
        return False, "Adresse nicht gefunden."

    data = results[0]
    addr = data.get("address", {})

    # --- STRIKTE PRÜFUNG FIX ---
    osm_plz = addr.get("postcode")
    osm_ort = addr.get("city") or addr.get("town") or addr.get("village")

    if plz and osm_plz and osm_plz != plz:
        return False, f"PLZ stimmt nicht überein (gefunden: {osm_plz})."

    if ort and osm_ort and osm_ort.lower() != ort.lower():
        return False, f"Ort stimmt nicht überein (gefunden: {osm_ort})."

    return True, None
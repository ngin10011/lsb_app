# services/address_validation.py
import requests
from flask import current_app

def _norm(s: str | None) -> str:
    """Einfache Normalisierung für String-Vergleiche."""
    if not s:
        return ""
    return " ".join(s.strip().lower().split())  # trim + Mehrfachspaces weg

def check_address_exists(strasse, hausnummer, plz, ort):
    """
    Prüft eine Adresse über Nominatim.

    Rückgabe:
      ok = True   -> alles konsistent, msg = None oder Hinweis
      ok = False  -> Adresse *gar nicht gefunden*, msg = Fehlermeldung (harte Validierung)
      ok = None   -> Dienst nicht erreichbar ODER Abweichungen; Soft-Fail mit Warnung
    """
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
        # Soft-Fail: Dienst nicht erreichbar
        return None, "Adressdienst aktuell nicht erreichbar, Adresse wurde ohne Prüfung übernommen."

    try:
        results = resp.json()
    except ValueError:
        # JSON-Fehler o. ä. → ebenfalls Soft-Fail
        return None, "Adressdienst liefert ungültige Antwort, Adresse wurde ohne Prüfung übernommen."

    # -> Harter Fehler: nichts gefunden
    if not results:
        return False, "Adresse nicht gefunden."

    data = results[0]
    addr = data.get("address", {}) or {}

    # Werte aus Nominatim
    osm_strasse = addr.get("road") or addr.get("pedestrian") or addr.get("footway")
    osm_hausnr  = addr.get("house_number")
    osm_plz     = addr.get("postcode")
    osm_ort     = addr.get("city") or addr.get("town") or addr.get("village")

    errors = []

    # Straße
    if strasse and osm_strasse:
        if _norm(strasse) != _norm(osm_strasse):
            errors.append(f"Straße stimmt nicht überein (gefunden: {osm_strasse}).")
    elif strasse and not osm_strasse:
        errors.append("Straße konnte vom Adressdienst nicht bestimmt werden.")

    # Hausnummer
    if hausnummer and osm_hausnr:
        if _norm(hausnummer) != _norm(osm_hausnr):
            errors.append(f"Hausnummer stimmt nicht überein (gefunden: {osm_hausnr}).")
    elif hausnummer and not osm_hausnr:
        errors.append("Hausnummer konnte vom Adressdienst nicht bestimmt werden.")

    # PLZ
    if plz and osm_plz:
        if _norm(plz) != _norm(osm_plz):
            errors.append(f"PLZ stimmt nicht überein (gefunden: {osm_plz}).")
    elif plz and not osm_plz:
        errors.append("PLZ konnte vom Adressdienst nicht bestimmt werden.")

    # Ort
    if ort and osm_ort:
        if _norm(ort) != _norm(osm_ort):
            errors.append(f"Ort stimmt nicht überein (gefunden: {osm_ort}).")
    elif ort and not osm_ort:
        errors.append("Ort konnte vom Adressdienst nicht bestimmt werden.")

    if errors:
        # ➜ Soft-Fail: Abweichung anzeigen, aber Speichern ermöglichen
        return None, " ".join(errors)

    return True, None

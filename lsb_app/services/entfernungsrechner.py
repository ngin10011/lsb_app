# lsb_app/services/entfernungsrechner.py

from flask import current_app

# import os
# import pyodbc
import openrouteservice
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time
# from PyQt6.QtWidgets import QMessageBox
# from config.settings import STARTADRESSE
import logging

logger = logging.getLogger(__name__)

def berechne_entfernung(strasse, plz, ort):
    logger.info(f"Starte Entfernungsermittlung für: {strasse}, {plz} {ort}")

    # ➤ Konstanten
    # STARTADRESSE = "Steinsdorfstraße 15, 80538 München"
    # ORS_API_KEY = "5b3ce3597851110001cf6248368578c7b7934ccbb367202accb3655d"
    # ORS_API_KEY = os.getenv("ORS_API_KEY")
    ORS_API_KEY = current_app.config["ORS_API_KEY"]
    STARTADRESSE = current_app.config["STARTADRESSE"]
   
    fahrstrecke_km = None


    # ➤ Geocoder und ORS-Client
    geolocator = Nominatim(user_agent="routing-script")
    client = openrouteservice.Client(key=ORS_API_KEY)

    # ➤ Startadresse einmalig geokodieren
    start_loc = geolocator.geocode(STARTADRESSE)
    if not start_loc:
        logger.error("Startadresse konnte nicht geokodiert werden.")
        raise Exception("Startadresse konnte nicht geokodiert werden")
    coords_start = (start_loc.longitude, start_loc.latitude)

    logger.debug(f"Startadresse: {STARTADRESSE} → Koordinaten: {coords_start}")

    zieladresse = f"{strasse}, {plz} {ort}"
    try:
        ziel_loc = geolocator.geocode(zieladresse)
        if not ziel_loc:
            logger.error(f"Zieladresse nicht gefunden: {zieladresse}")
            # QMessageBox.information(parent, "Fehler", f"⚠️ Zieladresse nicht gefunden ({zieladresse})")
            print(f"⚠️ Fehler: Zieladresse nicht gefunden ({zieladresse})")
        else:
            coords_ziel = (ziel_loc.longitude, ziel_loc.latitude)
            logger.debug(f"Zieladresse: {zieladresse} → Koordinaten: {coords_ziel}")

            # ➤ Fahrstrecke mit ORS berechnen
            route = client.directions(
                coordinates=[coords_start, coords_ziel],
                profile='driving-car',
                format='geojson',
                preference='shortest'
            )
            fahrstrecke_km = round(route['features'][0]['properties']['segments'][0]['distance'] / 1000)
            logger.info(f"Fahrstrecke berechnet: {fahrstrecke_km} km von Start zu {zieladresse}")

    except Exception as e:
        logger.error(f"Fehler bei der Entfernungsermittlung für {zieladresse}: {e}")
        # QMessageBox.warning(parent, "Fehler", f"❌ Fehler: {e}")
        print(f"❌ Fehler: {e}")
    
    return fahrstrecke_km

# def pruefe_zieladresse(parent, strasse, plz, ort):
#     logger.info(f"Starte Adressprüfung für: {strasse}, {plz} {ort}")

#     geolocator = Nominatim(user_agent="routing-script")
#     zieladresse = f"{strasse}, {plz} {ort}"

#     try:
#         ziel_loc = geolocator.geocode(zieladresse)
#         if not ziel_loc:
#             logger.warning(f"Zieladresse nicht gefunden: {zieladresse}")
#             QMessageBox.information(parent, "Fehler", f"⚠️ Zieladresse nicht gefunden ({zieladresse})")
#             return False
#         else:
#             logger.info(f"Zieladresse gefunden: {zieladresse}")
#             QMessageBox.information(parent, "Valide Adresse", f"{zieladresse} gefunden")
#             return True

#     except Exception as e:
#         logger.error(f"Fehler bei der Adressprüfung für {zieladresse}: {e}")
#         QMessageBox.warning(parent, "Fehler", f"❌ Fehler: {e}")
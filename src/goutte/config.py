"""Paramètres centraux du MVP Goutte d'eau."""
from pathlib import Path
import os

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_DONNEES = RACINE / "data"
DOSSIER_MODELES = RACINE / "models"
DOSSIER_RAPPORTS = RACINE / "reports"

CHEMIN_BDD = Path(os.getenv("GOUTTE_DB", DOSSIER_DONNEES / "goutte.db"))
CHEMIN_MODELE = DOSSIER_MODELES / "modele_pluie.joblib"
CHEMIN_METRIQUES = DOSSIER_MODELES / "metriques.json"

REGION = "Île-de-France"
FUSEAU = "Europe/Paris"  # affichage en heure locale pour les agriculteurs

# Stations Infoclimat retenues pour la région (export du 01/09 au 30/09/2026)
STATIONS = {
    "00081": "Verneuil-sur-Seine",
    "00089": "Villemoisson-sur-Orge",
    "000NV": "Triel-sur-Seine - L'Hautil",
    "000OM": "Le Perreux-sur-Marne",
    "000P7": "Argenteuil",
    "000TC": "Plaisir (2)",
    "ME098": "[MAE] ESPE - PARIS",
    "STATIC0001": "Herblay",
    "STATIC0103": "Lesches",
    "STATIC0296": "Breuil-en-Vexin - La Chartre",
}

# Seules les colonnes utiles au modèle sont conservées (sobriété des données)
COLONNES_UTILES = [
    "station_id", "dh_utc", "temperature", "pression", "humidite",
    "point_de_rosee", "vent_moyen", "vent_direction",
    "pluie_1h", "pluie_cumul_0h", "pluie_intensite",
]

# Bornes physiques plausibles : au-delà, la valeur est considérée comme aberrante
BORNES = {
    "temperature": (-40, 50),
    "pression": (950, 1060),
    "humidite": (0, 100),
    "point_de_rosee": (-50, 35),
    "vent_moyen": (0, 200),
    "vent_direction": (0, 360),
    "pluie_1h": (0, 150),
    "pluie_cumul_0h": (0, 400),
    "pluie_intensite": (0, 400),
}

SEUIL_PLUIE_MM = 0.2      # seuil de pluie mesurable (pluviomètre à auget)
HORIZON_H = 3             # on prédit la pluie dans les 3 heures qui suivent
RANDOM_STATE = 42

URL_API_INFOCLIMAT = "https://www.infoclimat.fr/opendata/"

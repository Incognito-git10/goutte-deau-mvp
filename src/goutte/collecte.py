"""Collecte des observations Infoclimat (API open data ou export CSV).

Usage :
    python -m goutte.collecte --csv data/export_infoclimat.csv
    python -m goutte.collecte --api --debut 2026-09-01 --fin 2026-09-30
L'appel API nécessite un jeton Infoclimat dans la variable INFOCLIMAT_TOKEN.
"""
from __future__ import annotations

import argparse
import io
import logging
import os
from pathlib import Path

import pandas as pd
import requests

from . import config, db, features, nettoyage

log = logging.getLogger(__name__)


def lire_csv_infoclimat(source: str | Path | io.StringIO) -> pd.DataFrame:
    """Lit un CSV au format Infoclimat (métadonnées '#', ligne d'unités sous l'en-tête)."""
    df = pd.read_csv(source, sep=";", comment="#", dtype=str, low_memory=False)
    # La 1re ligne de données contient les unités (string;YYYY-MM-DD...) : on l'écarte
    df = df[df["station_id"] != "string"]
    return df.reset_index(drop=True)


def telecharger_api(stations: list[str], debut: str, fin: str, token: str | None = None) -> pd.DataFrame:
    """Interroge l'API open data Infoclimat et renvoie les observations brutes."""
    token = token or os.getenv("INFOCLIMAT_TOKEN")
    if not token:
        raise RuntimeError("Jeton manquant : définir INFOCLIMAT_TOKEN")
    params = [("version", "2"), ("method", "get"), ("format", "csv"),
              ("start", debut), ("end", fin), ("token", token)]
    params += [("stations[]", s) for s in stations]
    rep = requests.get(config.URL_API_INFOCLIMAT, params=params, timeout=60)
    rep.raise_for_status()
    return lire_csv_infoclimat(io.StringIO(rep.text))


def executer(df_brut: pd.DataFrame, chemin_bdd: Path = config.CHEMIN_BDD) -> dict:
    """Nettoie, enregistre les observations dans SQLite et met à jour la table horaire. Renvoie un rapport qualité."""
    propre, rapport = nettoyage.nettoyer(df_brut)
    with db.connexion(chemin_bdd) as cx:
        db.creer_schema(cx)
        db.enregistrer_stations(cx, config.STATIONS)
        n = db.enregistrer_observations(cx, propre)
        # Table horaire lue par le modèle et l'API, recalculée à chaque collecte
        horaire = features.agreger_horaire(db.lire_observations(cx))
        h = db.enregistrer_horaires(cx, horaire)
        # Contrôle qualité des pluviomètres, mémorisé dans la table stations
        qualite = features.controle_pluviometres(horaire)
        db.enregistrer_stations(cx, config.STATIONS, qualite)
    rapport["lignes_enregistrees"] = n
    rapport["mesures_horaires"] = h
    rapport["pluviometres"] = qualite
    log.info("Rapport collecte : %s", rapport)
    return rapport


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--csv", type=Path, help="chemin d'un export CSV Infoclimat")
    g.add_argument("--api", action="store_true", help="collecte via l'API Infoclimat")
    p.add_argument("--debut", default="2026-09-01")
    p.add_argument("--fin", default="2026-09-30")
    a = p.parse_args()
    brut = lire_csv_infoclimat(a.csv) if a.csv else telecharger_api(list(config.STATIONS), a.debut, a.fin)
    print(executer(brut))


if __name__ == "__main__":
    main()

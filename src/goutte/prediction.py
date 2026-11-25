"""Service de prévision : calcule le risque de pluie heure par heure pour une date donnée.

Ce module ne dépend ni de FastAPI ni de Streamlit, il est partagé par l'API et l'interface.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from . import config, db, features


class DateIndisponible(ValueError):
    """La date demandée n'est pas couverte par les observations en base."""


@lru_cache(maxsize=1)
def charger_modele(chemin: Path = config.CHEMIN_MODELE) -> dict:
    return joblib.load(chemin)


def charger_metriques() -> dict:
    return json.loads(config.CHEMIN_METRIQUES.read_text())


SEUIL_ELEVE = 0.5


def niveau(proba: float, seuil: float) -> str:
    """faible : sous le seuil d'alerte ; modéré : au-dessus du seuil (risque plusieurs fois supérieur
    à la normale) ; élevé : pluie plus probable qu'improbable."""
    if proba >= max(SEUIL_ELEVE, seuil):
        return "élevé"
    if proba >= seuil:
        return "modéré"
    return "faible"


def predire_jour(jour: date, station_id: str | None = None, chemin_bdd: Path = config.CHEMIN_BDD) -> dict:
    art = charger_modele()
    modele, seuil, variables = art["modele"], art["seuil"], art["variables"]

    with db.connexion(chemin_bdd) as cx:
        h = db.lire_horaires(cx, jour.isoformat())
        debut, fin = db.periode_disponible(cx)
        fiables = db.stations_pluie_fiables(cx)

    d = features.construire_variables(h, avec_cible=False, stations_pluie=fiables) if len(h) else h
    if len(d):
        d = d[d["heure_utc"].dt.date == jour]
        d = d.dropna(subset=["temperature", "humidite", "pression"])
    if station_id:
        d = d[d["station_id"] == station_id]
    if d is None or not len(d):
        raise DateIndisponible(f"Aucune observation exploitable le {jour} "
                               f"(données disponibles du {debut} au {fin}).")

    d = d.assign(proba=modele.predict_proba(d[variables])[:, 1])
    par_heure = (d.groupby("heure_utc")
                   .agg(proba=("proba", "mean"), proba_max=("proba", "max"), stations=("station_id", "nunique"))
                   .reset_index())

    risque_jour = float(par_heure["proba"].max())
    heures = [{
        "heure_utc": r.heure_utc.strftime("%H:%M"),
        "heure_locale": r.heure_utc.tz_localize("UTC").tz_convert(config.FUSEAU).strftime("%H:%M"),
        "probabilite": round(float(r.proba), 3),
        "probabilite_max_station": round(float(r.proba_max), 3),
        "niveau": niveau(float(r.proba), seuil),
        "stations": int(r.stations),
    } for r in par_heure.itertuples()]

    return {
        "date": jour.isoformat(),
        "region": config.REGION,
        "station_id": station_id,
        "horizon_h": config.HORIZON_H,
        "risque_journalier": round(risque_jour, 3),
        "niveau_journalier": niveau(risque_jour, seuil),
        "pluie_attendue": risque_jour >= seuil,
        "heures_a_risque": [x["heure_locale"] for x in heures if x["probabilite"] >= seuil],
        "seuil_decision": seuil,
        "modele": art["nom"],
        "previsions_horaires": heures,
    }


def stations_disponibles(chemin_bdd: Path = config.CHEMIN_BDD) -> list[dict]:
    with db.connexion(chemin_bdd) as cx:
        return db.lire_stations(cx).to_dict(orient="records")


def periode(chemin_bdd: Path = config.CHEMIN_BDD) -> tuple[str, str]:
    with db.connexion(chemin_bdd) as cx:
        return db.periode_disponible(cx)

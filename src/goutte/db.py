"""Accès à la base SQLite : schéma, écriture et lecture."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations (
    station_id   TEXT PRIMARY KEY,
    nom          TEXT NOT NULL,
    region       TEXT NOT NULL,
    qualite_pluie TEXT NOT NULL DEFAULT 'ok'
        CHECK (qualite_pluie IN ('ok', 'suspect', 'absent'))
);
CREATE TABLE IF NOT EXISTS observations (
    station_id     TEXT NOT NULL REFERENCES stations(station_id),
    dh_utc         TEXT NOT NULL,
    temperature    REAL,
    pression       REAL,
    humidite       REAL,
    point_de_rosee REAL,
    vent_moyen     REAL,
    vent_direction REAL,
    pluie_1h       REAL,
    pluie_mm       REAL,
    PRIMARY KEY (station_id, dh_utc)
);
CREATE TABLE IF NOT EXISTS mesures_horaires (
    station_id      TEXT NOT NULL REFERENCES stations(station_id),
    heure_utc       TEXT NOT NULL,
    temperature     REAL,
    humidite        REAL,
    point_de_rosee  REAL,
    pression        REAL,
    vent_moyen      REAL,
    vent_direction  REAL,
    pluie_mm_1h     REAL,
    PRIMARY KEY (station_id, heure_utc)
);
CREATE INDEX IF NOT EXISTS idx_mesures_heure ON mesures_horaires(heure_utc);
CREATE TABLE IF NOT EXISTS entrainements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date_execution TEXT NOT NULL DEFAULT (datetime('now')),
    modele        TEXT NOT NULL,
    seuil         REAL NOT NULL,
    roc_auc       REAL,
    pr_auc        REAL,
    rappel        REAL,
    precision     REAL,
    f1            REAL,
    brier         REAL
);
"""

COLS_OBS = ["station_id", "dh_utc", "temperature", "pression", "humidite",
            "point_de_rosee", "vent_moyen", "vent_direction", "pluie_1h", "pluie_mm"]


@contextmanager
def connexion(chemin: Path = config.CHEMIN_BDD):
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(chemin)
    cx.execute("PRAGMA foreign_keys = ON")
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()


def creer_schema(cx: sqlite3.Connection) -> None:
    cx.executescript(SCHEMA)


def enregistrer_stations(cx, stations: dict[str, str], qualite: dict[str, str] | None = None) -> None:
    qualite = qualite or {}
    cx.executemany(
        "INSERT OR REPLACE INTO stations (station_id, nom, region, qualite_pluie) VALUES (?, ?, ?, ?)",
        [(sid, nom, config.REGION, qualite.get(sid, "ok")) for sid, nom in stations.items()],
    )


def stations_pluie_fiables(cx) -> list[str]:
    """Stations dont le pluviomètre a passé le contrôle qualité (utilisées pour la cible)."""
    return [r[0] for r in cx.execute("SELECT station_id FROM stations WHERE qualite_pluie = 'ok'")]


def enregistrer_observations(cx, df: pd.DataFrame) -> int:
    d = df[COLS_OBS].copy()
    d["dh_utc"] = d["dh_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
    d = d.astype(object).where(d.notna(), None)
    cx.executemany(
        f"INSERT OR REPLACE INTO observations ({','.join(COLS_OBS)}) VALUES ({','.join('?' * len(COLS_OBS))})",
        d.itertuples(index=False, name=None),
    )
    return len(d)


def enregistrer_horaires(cx, df: pd.DataFrame) -> int:
    cols = ["station_id", "heure_utc", "temperature", "humidite", "point_de_rosee",
            "pression", "vent_moyen", "vent_direction", "pluie_mm_1h"]
    d = df[cols].copy()
    d["heure_utc"] = d["heure_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
    d = d.astype(object).where(d.notna(), None)
    cx.execute("DELETE FROM mesures_horaires")
    cx.executemany(
        f"INSERT INTO mesures_horaires ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        d.itertuples(index=False, name=None),
    )
    return len(d)


def lire_observations(cx) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM observations", cx, parse_dates=["dh_utc"])


def lire_horaires(cx, jour: str | None = None) -> pd.DataFrame:
    if jour is None:
        return pd.read_sql("SELECT * FROM mesures_horaires", cx, parse_dates=["heure_utc"])
    # On charge la veille pour pouvoir calculer les variables décalées (tendance 3 h)
    return pd.read_sql(
        "SELECT * FROM mesures_horaires WHERE heure_utc >= datetime(?, '-1 day') AND heure_utc < datetime(?, '+1 day')",
        cx, params=(jour, jour), parse_dates=["heure_utc"],
    )


def lire_stations(cx) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM stations ORDER BY station_id", cx)


def periode_disponible(cx) -> tuple[str | None, str | None]:
    return cx.execute("SELECT min(date(heure_utc)), max(date(heure_utc)) FROM mesures_horaires").fetchone()

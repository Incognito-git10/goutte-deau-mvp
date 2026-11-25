"""Nettoyage des observations brutes : colonnes utiles, types, doublons, valeurs aberrantes."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def nettoyer(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rapport = {"lignes_brutes": int(len(df))}

    df = df[[c for c in config.COLONNES_UTILES if c in df.columns]].copy()
    rapport["colonnes_conservees"] = len(df.columns)

    df["dh_utc"] = pd.to_datetime(df["dh_utc"], errors="coerce")
    for col in config.BORNES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["station_id", "dh_utc"])
    avant = len(df)
    df = df.drop_duplicates(subset=["station_id", "dh_utc"], keep="last")
    rapport["doublons_supprimes"] = int(avant - len(df))

    aberrantes = 0
    for col, (bas, haut) in config.BORNES.items():
        if col in df.columns:
            masque = df[col].notna() & ~df[col].between(bas, haut)
            aberrantes += int(masque.sum())
            df.loc[masque, col] = np.nan
    rapport["valeurs_aberrantes_neutralisees"] = aberrantes

    # Point de rosée manquant : formule de Magnus à partir de T et HR
    manque = df["point_de_rosee"].isna() & df["temperature"].notna() & df["humidite"].gt(0)
    df.loc[manque, "point_de_rosee"] = point_de_rosee(df.loc[manque, "temperature"], df.loc[manque, "humidite"])

    df = df.sort_values(["station_id", "dh_utc"]).reset_index(drop=True)
    df["pluie_mm"] = pluie_par_pas(df)

    rapport["lignes_propres"] = int(len(df))
    rapport["taux_completude"] = {
        c: round(float(df[c].notna().mean()), 3)
        for c in ["temperature", "pression", "humidite", "point_de_rosee", "vent_moyen"]
    }
    return df, rapport


def point_de_rosee(t: pd.Series, hr: pd.Series) -> pd.Series:
    a, b = 17.27, 237.7
    gamma = a * t / (b + t) + np.log(hr / 100.0)
    return (b * gamma / (a - gamma)).round(1)


def pluie_par_pas(df: pd.DataFrame) -> pd.Series:
    """Hauteur de pluie tombée depuis la mesure précédente (mm), en secours de pluie_1h.

    Le cumul depuis 0 h est différencié par station et par jour ; quand il n'est pas
    disponible, on se rabat sur l'intensité instantanée convertie sur la durée du pas.
    L'intensité instantanée surestime les averses brèves : l'agrégation horaire
    privilégie donc toujours la mesure pluie_1h du pluviomètre quand elle existe.
    """
    jour = df["dh_utc"].dt.date
    cumul = df.groupby(["station_id", jour])["pluie_cumul_0h"]
    diff = cumul.diff()
    premier = cumul.cumcount() == 0
    diff = diff.where(~premier, df["pluie_cumul_0h"]).clip(lower=0)

    pas_h = df.groupby("station_id")["dh_utc"].diff().dt.total_seconds().div(3600).clip(upper=1).fillna(1 / 6)
    via_intensite = (df["pluie_intensite"] * pas_h).round(2)
    # NaN si la station ne transmet aucune donnée de pluie (pas de pluviomètre)
    return diff.fillna(via_intensite).where(df["pluie_1h"].notna() | diff.notna() | via_intensite.notna())

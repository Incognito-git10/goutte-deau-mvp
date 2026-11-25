"""Agrégation horaire et construction des variables explicatives / de la cible."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

FEATURES = [
    "temperature", "humidite", "ecart_rosee", "pression", "tendance_pression_3h",
    "vent_moyen", "vent_sin", "vent_cos", "pluie_mm_1h", "pluie_mm_3h_passees",
    "heure_sin", "heure_cos",
    "pluie_region_1h", "nb_stations_pluie", "tendance_pression_region",
]
CIBLE = "pluie_3h_suivantes"


def agreger_horaire(obs: pd.DataFrame) -> pd.DataFrame:
    """Ramène chaque station à un pas horaire régulier (moyenne, dernière valeur ou somme).

    La ligne étiquetée hh:00 décrit l'intervalle [hh:00, hh+1:00[. La pluie horaire vient en priorité
    de pluie_1h, publié à hh+1:00 pour l'heure écoulée ; à défaut, de la somme des pluies par pas.
    """
    morceaux = []
    for sid, g in obs.groupby("station_id"):
        g = g.set_index("dh_utc").sort_index()
        pluie_pas = g["pluie_mm"].resample("h").sum(min_count=1)
        if "pluie_1h" in g:
            p1h = g.loc[g.index.minute == 0, "pluie_1h"].dropna()
            p1h.index = p1h.index - pd.Timedelta(hours=1)
            pluie = p1h.reindex(pluie_pas.index).combine_first(pluie_pas)
        else:
            pluie = pluie_pas
        h = pd.DataFrame({
            "temperature": g["temperature"].resample("h").mean(),
            "humidite": g["humidite"].resample("h").mean(),
            "point_de_rosee": g["point_de_rosee"].resample("h").mean(),
            "pression": g["pression"].resample("h").last(),
            "vent_moyen": g["vent_moyen"].resample("h").mean(),
            "vent_direction": g["vent_direction"].resample("h").last(),
            "pluie_mm_1h": pluie,
        })
        # Petits trous (≤ 2 h) comblés par interpolation, pas au-delà
        cont = ["temperature", "humidite", "point_de_rosee", "pression", "vent_moyen"]
        h[cont] = h[cont].interpolate(limit=2, limit_area="inside")
        h["station_id"] = sid
        morceaux.append(h.reset_index(names="heure_utc"))
    return pd.concat(morceaux, ignore_index=True)


def controle_pluviometres(h: pd.DataFrame, jours_min: int = 2, voisins_min: int = 3) -> dict[str, str]:
    """Contrôle qualité des pluviomètres sur la période.

    absent  : aucune mesure de pluie ;
    suspect : cumul nul alors qu'au moins `voisins_min` autres stations ont mesuré de la pluie
              (≥ 0,2 mm) au moins `jours_min` jours où la station transmettait (capteur bouché ou en panne).
    """
    d = h.assign(jour=h["heure_utc"].dt.date)
    journalier = d.groupby(["jour", "station_id"])["pluie_mm_1h"].sum(min_count=1).unstack()
    present = d.pivot_table(index="jour", columns="station_id", values="temperature", aggfunc="count").fillna(0) > 0
    statut = {}
    for sid in journalier.columns.union(present.columns):
        if sid not in journalier or journalier[sid].isna().all():
            statut[sid] = "absent"
            continue
        autres = journalier.drop(columns=sid)
        jours_pluvieux = (autres >= config.SEUIL_PLUIE_MM).sum(axis=1) >= voisins_min
        jours_pluvieux &= present[sid].reindex(jours_pluvieux.index, fill_value=False)
        if journalier[sid].sum() == 0 and jours_pluvieux.sum() >= jours_min:
            statut[sid] = "suspect"
        else:
            statut[sid] = "ok"
    return statut


def construire_variables(h: pd.DataFrame, avec_cible: bool = True,
                         stations_pluie: list[str] | None = None) -> pd.DataFrame:
    """Variables explicatives (et cible). `stations_pluie` : pluviomètres fiables, seuls pris en compte
    dans le contexte régional et la cible."""
    h = h.sort_values(["station_id", "heure_utc"]).copy()
    if stations_pluie is not None:
        h.loc[~h["station_id"].isin(stations_pluie), "pluie_mm_1h"] = np.nan
    g = h.groupby("station_id")
    h["ecart_rosee"] = h["temperature"] - h["point_de_rosee"]
    h["tendance_pression_3h"] = h["pression"] - g["pression"].shift(3)
    rad = np.deg2rad(h["vent_direction"].fillna(0))
    calme = h["vent_moyen"].fillna(0) == 0
    h["vent_sin"] = np.where(calme, 0, np.sin(rad))
    h["vent_cos"] = np.where(calme, 0, np.cos(rad))
    pluie_brute = h["pluie_mm_1h"]
    h["pluie_mm_1h"] = pluie_brute.fillna(0)
    h["pluie_mm_3h_passees"] = g["pluie_mm_1h"].transform(lambda s: s.fillna(0).rolling(3, min_periods=1).sum())
    heure = h["heure_utc"].dt.hour
    h["heure_sin"] = np.sin(2 * np.pi * heure / 24)
    h["heure_cos"] = np.cos(2 * np.pi * heure / 24)
    # Contexte régional : une averse détectée sur une station voisine annonce souvent la suivante
    h["_pluie_mesuree"] = pluie_brute
    par_heure = h.groupby("heure_utc")
    h["pluie_region_1h"] = par_heure["_pluie_mesuree"].transform("mean").fillna(0)
    h["nb_stations_pluie"] = par_heure["_pluie_mesuree"].transform(lambda s: (s >= config.SEUIL_PLUIE_MM).sum())
    h["tendance_pression_region"] = par_heure["tendance_pression_3h"].transform("mean")
    if avec_cible:
        futur = sum(g["pluie_mm_1h"].shift(-k).fillna(0) for k in range(1, config.HORIZON_H + 1))
        dispo = g["heure_utc"].shift(-config.HORIZON_H).notna()
        h[CIBLE] = (futur >= config.SEUIL_PLUIE_MM).astype(int)
        h = h[dispo]
        if stations_pluie is not None:
            h = h[h["station_id"].isin(stations_pluie)]
    return h.drop(columns="_pluie_mesuree")


def jeu_entrainement(h: pd.DataFrame, stations_pluie: list[str] | None = None) -> pd.DataFrame:
    d = construire_variables(h, stations_pluie=stations_pluie)
    # Lignes sans les mesures de base inutilisables (station en panne ou sans hygromètre)
    return d.dropna(subset=["temperature", "humidite", "pression"]).reset_index(drop=True)

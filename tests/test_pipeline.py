import io
from datetime import date

import numpy as np
import pandas as pd
import pytest

from goutte import collecte, config, features, nettoyage

CSV = """# METADATA:
# Source: www.infoclimat.fr
station_id;dh_utc;temperature;pression;humidite;point_de_rosee;vent_moyen;vent_direction;pluie_1h;pluie_cumul_0h;pluie_intensite;uv
string;YYYY-MM-DD hh:mm:ss;°C;hPa;%;°C;km/h;deg;mm;mm;mm/h;W/m²
A;2026-09-01 00:00:00;15;1015;80;11.6;5;180;;0;0;0
A;2026-09-01 00:30:00;15;1015;80;;5;180;;0.4;2;0
A;2026-09-01 00:30:00;15;1015;80;;5;180;;0.4;2;0
A;2026-09-01 01:00:00;99;1015;150;11;5;180;;0.6;0;0
"""


@pytest.fixture
def brut():
    return collecte.lire_csv_infoclimat(io.StringIO(CSV))


def test_lecture_ignore_ligne_unites(brut):
    assert (brut["station_id"] != "string").all()
    assert len(brut) == 4


def test_nettoyage(brut):
    df, rapport = nettoyage.nettoyer(brut)
    assert "uv" not in df.columns                      # colonnes inutiles supprimées
    assert rapport["doublons_supprimes"] == 1
    assert rapport["valeurs_aberrantes_neutralisees"] == 2  # 99 °C et 150 %
    assert df["point_de_rosee"].notna().iloc[1]        # rosée recalculée (Magnus)
    assert df["pluie_mm"].tolist() == pytest.approx([0, 0.4, 0.2])


def test_point_de_rosee_magnus():
    assert nettoyage.point_de_rosee(pd.Series([20.0]), pd.Series([50.0])).iloc[0] == pytest.approx(9.3, abs=0.1)


def test_variables_et_cible():
    heures = pd.date_range("2026-09-01", periods=10, freq="h")
    h = pd.DataFrame({"station_id": "A", "heure_utc": heures, "temperature": 15.0, "humidite": 80.0,
                      "point_de_rosee": 11.0, "pression": np.linspace(1015, 1010, 10), "vent_moyen": 5.0,
                      "vent_direction": 90.0, "pluie_mm_1h": [0, 0, 0, 0, 0.5, 0, 0, 0, 0, 0]})
    d = features.construire_variables(h)
    assert set(features.FEATURES) <= set(d.columns)
    # La pluie de 04:00 doit être annoncée à 01:00, 02:00 et 03:00 (horizon 3 h), pas à 00:00
    assert d.set_index("heure_utc")[features.CIBLE].iloc[:5].tolist() == [0, 1, 1, 1, 0]
    assert len(d) == 10 - config.HORIZON_H


@pytest.mark.skipif(not config.CHEMIN_MODELE.exists(), reason="modèle non entraîné")
def test_prediction_bout_en_bout():
    from goutte import prediction
    r = prediction.predire_jour(date(2026, 9, 30))
    assert 0 <= r["risque_journalier"] <= 1
    assert r["niveau_journalier"] in {"faible", "modéré", "élevé"}
    assert len(r["previsions_horaires"]) > 0
    with pytest.raises(prediction.DateIndisponible):
        prediction.predire_jour(date(1999, 1, 1))


def test_pluie_horaire_privilegie_pluie_1h():
    # pluie_1h publié à 01:00 = pluie de 00:00 à 01:00 ; l'intensité instantanée (60 mm/h) est ignorée
    obs = pd.DataFrame({
        "station_id": "A",
        "dh_utc": pd.to_datetime(["2026-09-01 00:00", "2026-09-01 00:30", "2026-09-01 01:00"]),
        "temperature": 15.0, "humidite": 80.0, "point_de_rosee": 11.0, "pression": 1015.0,
        "vent_moyen": 5.0, "vent_direction": 90.0,
        "pluie_1h": [np.nan, np.nan, 1.2], "pluie_mm": [0.0, 30.0, 0.0],
    })
    h = features.agreger_horaire(obs).set_index("heure_utc")
    assert h.loc["2026-09-01 00:00", "pluie_mm_1h"] == pytest.approx(1.2)


def test_controle_pluviometres():
    heures = pd.date_range("2026-09-01", periods=72, freq="h")
    lignes = []
    for sid in ["A", "B", "C", "D"]:
        pluie = np.zeros(72)
        if sid != "D":                      # D ne mesure jamais rien alors que A, B, C mesurent
            pluie[[10, 40]] = 1.0           # de la pluie deux jours différents
        lignes.append(pd.DataFrame({"station_id": sid, "heure_utc": heures, "temperature": 15.0,
                                    "pluie_mm_1h": pluie}))
    lignes.append(pd.DataFrame({"station_id": "E", "heure_utc": heures, "temperature": 15.0,
                                "pluie_mm_1h": np.nan}))
    statut = features.controle_pluviometres(pd.concat(lignes))
    assert statut == {"A": "ok", "B": "ok", "C": "ok", "D": "suspect", "E": "absent"}

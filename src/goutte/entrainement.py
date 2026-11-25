"""Préparation du jeu horaire, entraînement, sélection et évaluation du modèle.

Usage : python -m goutte.entrainement
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, fbeta_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config, db, features

log = logging.getLogger(__name__)
DATE_COUPURE = "2026-09-23"  # test de robustesse : appris sur 1er–22 sept., testé sur 23–30 sept.


def candidats() -> dict:
    rs = config.RANDOM_STATE
    return {
        "regression_logistique": make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.5, max_iter=1000)),
        # Pas de pondération des classes : les probabilités restent calibrées (score de Brier),
        # ce qui compte pour une API qui restitue un risque en pourcentage.
        "foret_aleatoire": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=10,
                                   n_jobs=1, random_state=rs)),
    }


def preparer(chemin_bdd=config.CHEMIN_BDD) -> pd.DataFrame:
    with db.connexion(chemin_bdd) as cx:
        horaire = db.lire_horaires(cx)
        fiables = db.stations_pluie_fiables(cx)
    return features.jeu_entrainement(horaire, fiables)


def metriques(y, proba, seuil) -> dict:
    pred = (proba >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": round(float(roc_auc_score(y, proba)), 3),
        "pr_auc": round(float(average_precision_score(y, proba)), 3),
        "rappel": round(float(recall_score(y, pred, zero_division=0)), 3),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 3),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 3),
        "f2": round(float(fbeta_score(y, pred, beta=2, zero_division=0)), 3),
        "brier": round(float(brier_score_loss(y, proba)), 4),
        "matrice_confusion": {"VN": int(tn), "FP": int(fp), "FN": int(fn), "VP": int(tp)},
    }


def proba_hors_echantillon(modele, X, y, groupes) -> np.ndarray:
    """Probabilités out-of-fold, validation croisée groupée par jour (pas de fuite intra-journée)."""
    oof = np.zeros(len(y))
    for tr, va in GroupKFold(n_splits=5).split(X, y, groupes):
        m = clone(modele).fit(X.iloc[tr], y.iloc[tr])
        oof[va] = m.predict_proba(X.iloc[va])[:, 1]
    return oof


def meilleur_seuil(y, proba) -> float:
    """Seuil qui maximise le F2 : on privilégie le rappel (rater une pluie coûte plus cher à l'agriculteur)."""
    grille = np.arange(0.05, 0.96, 0.01)
    scores = [fbeta_score(y, proba >= s, beta=2, zero_division=0) for s in grille]
    return round(float(grille[int(np.argmax(scores))]), 2)


def entrainer(chemin_bdd=config.CHEMIN_BDD) -> dict:
    d = preparer(chemin_bdd)
    X, y = d[features.FEATURES], d[features.CIBLE]
    jours = d["heure_utc"].dt.date

    # 1) Comparaison des candidats : validation croisée groupée par jour sur tout le mois
    resultats, oofs = {}, {}
    for nom, modele in candidats().items():
        oof = proba_hors_echantillon(modele, X, y, jours)
        seuil = meilleur_seuil(y, oof)
        oofs[nom] = oof
        resultats[nom] = {"seuil": seuil, "validation_croisee": metriques(y, oof, seuil)}
        log.info("%s CV : %s", nom, resultats[nom]["validation_croisee"])

    persistance = (d["pluie_mm_1h"] >= config.SEUIL_PLUIE_MM).astype(float).values
    climato = np.full(len(y), y.mean())
    references = {"persistance": metriques(y, persistance, 0.5),
                  "climatologie": metriques(y, climato, 0.5)}

    choisi = max(resultats, key=lambda n: resultats[n]["validation_croisee"]["pr_auc"])
    seuil = resultats[choisi]["seuil"]

    # 2) Test de robustesse temporel : entraînement sur le passé, test sur la dernière semaine
    passe, futur = d[d["heure_utc"] < DATE_COUPURE], d[d["heure_utc"] >= DATE_COUPURE]
    m_temp = clone(candidats()[choisi]).fit(passe[features.FEATURES], passe[features.CIBLE])
    p_temp = m_temp.predict_proba(futur[features.FEATURES])[:, 1]
    test_temporel = metriques(futur[features.CIBLE], p_temp, seuil)
    test_temporel["persistance"] = metriques(
        futur[features.CIBLE], (futur["pluie_mm_1h"] >= config.SEUIL_PLUIE_MM).astype(float), 0.5)

    # 3) Modèle final entraîné sur l'ensemble du mois
    final = clone(candidats()[choisi]).fit(X, y)

    importances = None
    est = final[-1]
    if hasattr(est, "feature_importances_"):
        importances = dict(sorted(zip(features.FEATURES, est.feature_importances_.round(3).tolist()),
                                  key=lambda kv: -kv[1]))
    elif hasattr(est, "coef_"):
        importances = dict(sorted(zip(features.FEATURES, est.coef_[0].round(3).tolist()),
                                  key=lambda kv: -abs(kv[1])))

    cv = resultats[choisi]["validation_croisee"]
    rapport = {
        "date_entrainement": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modele_retenu": choisi,
        "seuil_decision": seuil,
        "horizon_h": config.HORIZON_H,
        "seuil_pluie_mm": config.SEUIL_PLUIE_MM,
        "jeu": {
            "lignes": int(len(d)), "positifs": int(y.sum()),
            "taux_pluie": round(float(y.mean()), 3),
            "jours_avec_pluie": int(d.loc[y == 1, "heure_utc"].dt.date.nunique()),
            "stations": sorted(d["station_id"].unique().tolist()),
            "periode": [str(d["heure_utc"].min()), str(d["heure_utc"].max())],
        },
        "candidats": resultats,
        "evaluation": cv,
        "references": references,
        "test_temporel": test_temporel,
        "importance_variables": importances,
        "variables": features.FEATURES,
    }

    config.DOSSIER_MODELES.mkdir(exist_ok=True)
    joblib.dump({"modele": final, "seuil": seuil, "variables": features.FEATURES,
                 "nom": choisi}, config.CHEMIN_MODELE)
    config.CHEMIN_METRIQUES.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
    d.assign(proba_oof=oofs[choisi])[["station_id", "heure_utc", features.CIBLE, "pluie_mm_1h", "proba_oof"]].to_csv(
        config.DOSSIER_MODELES / "predictions_validation.csv", index=False)

    with db.connexion(chemin_bdd) as cx:
        cx.execute("INSERT INTO entrainements (modele, seuil, roc_auc, pr_auc, rappel, precision, f1, brier) "
                   "VALUES (?,?,?,?,?,?,?,?)",
                   (choisi, seuil, cv["roc_auc"], cv["pr_auc"], cv["rappel"], cv["precision"], cv["f1"], cv["brier"]))
    return rapport


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = entrainer()
    print(json.dumps({k: r[k] for k in ["modele_retenu", "seuil_decision", "jeu", "evaluation", "references",
                                        "test_temporel", "importance_variables"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

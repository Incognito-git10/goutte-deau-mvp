"""Génère les graphiques d'évaluation dans reports/. Usage : python -m goutte.rapport"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from . import config, db  # noqa: E402

BLEU, GRIS, ORANGE = "#1f5f99", "#8a8f98", "#d9822b"


def _style(ax, titre):
    ax.set_title(titre, fontsize=11, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.25)


def generer() -> None:
    config.DOSSIER_RAPPORTS.mkdir(exist_ok=True)
    m = json.loads(config.CHEMIN_METRIQUES.read_text())
    p = pd.read_csv(config.DOSSIER_MODELES / "predictions_validation.csv", parse_dates=["heure_utc"])
    y, s = p["pluie_3h_suivantes"], p["proba_oof"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.8))
    fpr, tpr, _ = roc_curve(y, s)
    a1.plot(fpr, tpr, color=BLEU, label=f"Modèle (AUC {m['evaluation']['roc_auc']})")
    a1.plot([0, 1], [0, 1], ls="--", color=GRIS, label="Hasard")
    a1.set_xlabel("Taux de faux positifs"); a1.set_ylabel("Taux de vrais positifs (rappel)")
    _style(a1, "Courbe ROC"); a1.legend(frameon=False, fontsize=8)
    pr, rc, _ = precision_recall_curve(y, s)
    a2.plot(rc, pr, color=BLEU, label=f"Modèle (PR-AUC {m['evaluation']['pr_auc']})")
    a2.axhline(y.mean(), ls="--", color=GRIS, label=f"Climatologie ({y.mean():.3f})")
    ref = m["references"]["persistance"]
    a2.scatter([ref["rappel"]], [ref["precision"]], color=ORANGE, zorder=3, label="Persistance")
    e = m["evaluation"]
    a2.scatter([e["rappel"]], [e["precision"]], color=BLEU, zorder=3, marker="D",
               label=f"Seuil retenu ({m['seuil_decision']})")
    a2.set_xlabel("Rappel"); a2.set_ylabel("Précision")
    _style(a2, "Précision / rappel"); a2.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(config.DOSSIER_RAPPORTS / "courbes_roc_pr.png", dpi=160); plt.close(fig)

    imp = pd.Series(m["importance_variables"]).sort_values()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(imp.index, imp.values, color=BLEU)
    ax.set_xlabel("Importance (réduction d'impureté)")
    _style(ax, "Importance des variables – forêt aléatoire")
    fig.tight_layout(); fig.savefig(config.DOSSIER_RAPPORTS / "importance_variables.png", dpi=160); plt.close(fig)

    with db.connexion() as cx:
        h = db.lire_horaires(cx)
    reg = h.groupby("heure_utc").agg(pluie=("pluie_mm_1h", "mean"), pression=("pression", "mean"))
    proba = p.groupby("heure_utc")["proba_oof"].mean()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(reg.index, reg["pluie"], width=0.04, color=BLEU, label="Pluie moyenne observée (mm/h)")
    ax.set_ylabel("Pluie (mm/h)")
    ax2 = ax.twinx()
    ax2.plot(proba.index, proba.values, color=ORANGE, lw=1, label="Probabilité prédite (validation)")
    ax2.set_ylim(0, 1); ax2.set_ylabel("Probabilité")
    _style(ax, "Septembre 2026 – pluie observée et risque prédit (moyenne régionale)")
    ax2.spines[["top"]].set_visible(False)
    l1, n1 = ax.get_legend_handles_labels(); l2, n2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, n1 + n2, frameon=False, fontsize=8, loc="upper left")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(config.DOSSIER_RAPPORTS / "serie_pluie_proba.png", dpi=160); plt.close(fig)

    cm = m["evaluation"]["matrice_confusion"]
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    grille = [[cm["VN"], cm["FP"]], [cm["FN"], cm["VP"]]]
    ax.imshow(grille, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, grille[i][j], ha="center", va="center",
                    color="white" if grille[i][j] > 1000 else "black", fontsize=12)
    ax.set_xticks([0, 1], ["Pas de pluie", "Pluie"]); ax.set_yticks([0, 1], ["Pas de pluie", "Pluie"])
    ax.set_xlabel("Prédit"); ax.set_ylabel("Observé")
    ax.set_title("Matrice de confusion", fontsize=11, loc="left")
    fig.tight_layout(); fig.savefig(config.DOSSIER_RAPPORTS / "matrice_confusion.png", dpi=160); plt.close(fig)


def exemple_prevision(jour: str = "2026-09-30") -> None:
    """Graphique de la prévision horaire d'une journée, tel que restitué par l'API."""
    from datetime import date
    from . import prediction
    r = prediction.predire_jour(date.fromisoformat(jour))
    df = pd.DataFrame(r["previsions_horaires"])
    with db.connexion() as cx:
        h = db.lire_horaires(cx, jour)
        fiables = db.stations_pluie_fiables(cx)
    h = h[(h["heure_utc"].dt.date == date.fromisoformat(jour)) & h["station_id"].isin(fiables)]
    obs = h.groupby(h["heure_utc"].dt.strftime("%H:%M"))["pluie_mm_1h"].mean().reindex(df["heure_utc"])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(df["heure_locale"], obs.values, color=BLEU, alpha=0.6, label="Pluie observée (mm/h, moyenne)")
    ax.set_ylabel("Pluie (mm/h)")
    ax2 = ax.twinx()
    ax2.plot(df["heure_locale"], df["probabilite"], color=ORANGE, marker="o", ms=3,
             label="Probabilité de pluie dans les 3 h")
    ax2.axhline(r["seuil_decision"], color=GRIS, ls="--", lw=1, label=f"Seuil d'alerte ({r['seuil_decision']:.0%})")
    ax2.set_ylim(0, 1); ax2.set_ylabel("Probabilité")
    ax.set_xlabel("Heure de Paris")
    ax.tick_params(axis="x", labelsize=7, rotation=90)
    _style(ax, f"Prévision restituée par l'API pour le {jour} – Île-de-France")
    ax2.spines[["top"]].set_visible(False)
    l1, n1 = ax.get_legend_handles_labels(); l2, n2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, n1 + n2, frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(config.DOSSIER_RAPPORTS / f"prevision_{jour}.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    generer()
    exemple_prevision()

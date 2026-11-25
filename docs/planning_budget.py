"""Planning (Gantt), calendrier des sprints et budget prévisionnel par phase du projet Goutte d'eau.

Les jalons, rôles, jours et coûts reprennent le cahier des charges (bloc 1) : J1 12/02/2027,
J2 09/04/2027, J3 19/07/2027, J4 26/11/2027 ; 1 655 jours, 1 352 000 € provision comprise.
Le MVP (phase préliminaire, nov.-déc. 2026) est chiffré à part.

Usage : python docs/planning_budget.py  →  docs/gantt.png, docs/planning.csv, docs/sprints.csv,
        docs/budget_rh.csv, docs/budget_autres.csv, docs/budget_phases.csv
"""
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ICI = Path(__file__).parent
D = date.fromisoformat

PHASES = {
    "MVP": "Phase préliminaire – MVP (preuve de concept)",
    "P0": "Phase 0 – Cadrage et recueil des besoins",
    "P1": "Phase 1 – Socle data (sprints 1 à 4)",
    "P2": "Phase 2 – Modélisation IA (sprints 3 à 10)",
    "P3": "Phase 3 – Produit (sprints 5 à 10)",
    "P4": "Phase 4 – Sécurité, conformité, recette",
    "P5": "Phase 5 – Pilote terrain (Kanban)",
    "P6": "Phase 6 – Évaluation et bilan",
}
COULEURS = {"MVP": "#5b6470", "P0": "#8a8f98", "P1": "#1f5f99", "P2": "#2e8b6e", "P3": "#d9822b",
            "P4": "#7b4fa3", "P5": "#b8404b", "P6": "#4a4a4a"}

# (phase, tâche, début, fin)
TACHES = [
    ("MVP", "Sprint A : collecte API, SQLite, nettoyage, exploration", "2026-11-16", "2026-11-27"),
    ("MVP", "Sprint B : modèle, API FastAPI, Streamlit, documentation", "2026-11-30", "2026-12-11"),
    ("MVP", "Revue du MVP et décision de lancement", "2026-12-14", "2026-12-18"),
    ("P0", "Paramétrage des outils collaboratifs (GitHub, Tchap)", "2027-01-04", "2027-01-15"),
    ("P0", "Entretiens, questionnaires, ateliers", "2027-01-04", "2027-02-05"),
    ("P0", "Cahier des charges v2 et validation COPIL", "2027-01-25", "2027-02-12"),
    ("P0", "Registre RGPD, lancement de l'AIPD", "2027-01-18", "2027-02-26"),
    ("P1", "Ingestion IoT temps réel et contrôle qualité", "2027-02-15", "2027-03-26"),
    ("P1", "Lac de données, historique 5 ans, référentiel capteurs", "2027-02-15", "2027-04-09"),
    ("P2", "Modèle de référence et protocole d'évaluation", "2027-03-15", "2027-04-09"),
    ("P2", "Prévision immédiate 0-6 h et descente d'échelle 1 km", "2027-04-12", "2027-06-18"),
    ("P2", "MLOps : réentraînement, suivi de dérive", "2027-04-19", "2027-07-02"),
    ("P3", "Application mobile / web (RGAA)", "2027-04-12", "2027-07-02"),
    ("P3", "Moteur d'alertes et API collectivités", "2027-04-26", "2027-07-02"),
    ("P4", "Mode miroir et mesure RMSE / MAE", "2027-06-07", "2027-07-16"),
    ("P4", "Test d'intrusion, homologation, recette", "2027-06-07", "2027-07-16"),
    ("P5", "Exploitation et améliorations en flux", "2027-07-19", "2027-10-15"),
    ("P5", "Retours des 50 testeurs, points mensuels", "2027-07-19", "2027-10-15"),
    ("P6", "Enquête de satisfaction, mesure des KPI", "2027-10-11", "2027-11-05"),
    ("P6", "Rapport de bilan et décision de généralisation", "2027-11-01", "2027-11-26"),
]
JALONS = [("J0 Revue MVP", "2026-12-18"), ("J1 Cahier des charges", "2027-02-12"),
          ("J2 Socle data", "2027-04-09"), ("J3 Go pilote", "2027-07-19"), ("J4 Bilan", "2027-11-26")]

# Jours par rôle et par phase (P0..P6) – totaux identiques au cahier des charges
PH = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
ROLES = [  # rôle, statut, TJM, jours par phase
    ("Chef de projet / Data Scientist lead", "Interne", 750, [28, 30, 30, 25, 22, 55, 30]),
    ("Product Owner (prévisionniste senior)", "Interne", 650, [15, 10, 10, 20, 12, 28, 15]),
    ("Data Scientists (2)", "Interne + prestataire", 700, [10, 50, 140, 20, 40, 70, 30]),
    ("Data Engineer", "Prestataire", 650, [5, 70, 30, 30, 20, 35, 10]),
    ("Ingénieur MLOps / DevOps", "Prestataire", 700, [0, 15, 40, 20, 20, 20, 5]),
    ("Développeurs web et mobile (2)", "Prestataire", 600, [0, 0, 0, 160, 40, 40, 0]),
    ("Designer UX / UI", "Prestataire", 600, [5, 0, 0, 35, 5, 5, 0]),
    ("Météorologue expert", "Interne", 650, [5, 3, 15, 5, 12, 17, 3]),
    ("Technicien IoT", "Interne", 450, [10, 35, 5, 5, 5, 45, 5]),
    ("Testeur / QA", "Prestataire", 500, [0, 5, 0, 15, 30, 10, 0]),
    ("DPO et juriste", "Interne", 800, [6, 2, 1, 1, 6, 2, 2]),
    ("RSSI", "Interne", 800, [3, 2, 0, 1, 7, 1, 1]),
    ("Chargé de communication / panel", "Interne", 500, [8, 2, 2, 8, 10, 20, 10]),
    ("Coach agile (démarrage)", "Prestataire", 750, [15, 10, 5, 0, 0, 0, 0]),
]
# Postes non humains (cahier des charges, 153 600 €) répartis selon le calendrier
AUTRES = [
    ("Capteurs", "Étalonnage (400 × 25 €)", {"P1": 10000}),
    ("Capteurs", "Remplacement de capteurs défaillants (20 × 450 €)", {"P1": 4500, "P5": 4500}),
    ("Capteurs", "Densification ciblée (30 × 450 €)", {"P1": 13500}),
    ("Connectivité IoT", "400 × 1,5 €/mois × 11 mois", {"P0": 900, "P1": 1200, "P2": 900, "P3": 900,
                                                        "P4": 600, "P5": 1800, "P6": 300}),
    ("Cloud", "Entraînement (3 000 h GPU × 3,5 €)", {"P2": 9000, "P5": 1500}),
    ("Cloud", "Plateforme flux, calcul, API (3 500 €/mois × 9)", {"P1": 3500, "P2": 3500, "P3": 3500,
                                                                   "P4": 3500, "P5": 10500, "P6": 7000}),
    ("Cloud", "Stockage (20 To × 25 €/To/mois × 11)", {"P0": 500, "P1": 1000, "P2": 1000, "P3": 500,
                                                       "P4": 500, "P5": 1500, "P6": 500}),
    ("Postes de travail", "2 stations avec GPU", {"P0": 8000}),
    ("Logiciels", "Gestion de projet, design, supervision", {"P0": 6000}),
    ("Diffusion", "Passerelle SMS et notifications", {"P3": 1000, "P5": 2000}),
    ("Tests", "Terminaux mobiles", {"P3": 2000}),
    ("Sécurité", "Test d'intrusion et audit externe", {"P4": 18000}),
    ("Juridique", "Appui externe (AI Act, conventions)", {"P0": 3000, "P4": 3000}),
    ("Panel", "Indemnisation des 50 testeurs", {"P5": 10000}),
    ("Communication", "Lancement, ateliers, supports", {"P0": 2000, "P5": 5000, "P6": 2000}),
    ("Formation", "Utilisateurs et équipe", {"P0": 2000, "P4": 3000}),
]
PROVISION = 0.10
PROVISION_TOTALE = 122_900
# Phase préliminaire (MVP), hors budget du pilote
MVP = [("Chef de projet / Data Scientist lead", 750, 15), ("Data Engineer", 650, 3),
       ("Product Owner (prévisionniste senior)", 650, 2)]


def sprints() -> pd.DataFrame:
    debut = D("2027-02-15")
    lignes = []
    for i in range(11):
        d0 = debut + timedelta(weeks=2 * i)
        lignes.append({"sprint": f"S{i + 1}", "debut": d0, "fin": d0 + timedelta(days=11)})
    return pd.DataFrame(lignes)


def budget():
    rh = pd.DataFrame([{"role": r, "statut": s, "tjm": t, **dict(zip(PH, j)), "jours": sum(j),
                        "cout": t * sum(j)} for r, s, t, j in ROLES])
    autres = pd.DataFrame([{"poste": p, "detail": d, **{k: rep.get(k, 0) for k in PH},
                            "cout": sum(rep.values())} for p, d, rep in AUTRES])
    phases = pd.DataFrame({
        "phase": PH,
        "libelle": [PHASES[p] for p in PH],
        "jours": [int(rh[p].sum()) for p in PH],
        "humain": [int((rh[p] * rh["tjm"]).sum()) for p in PH],
        "autres": [int(autres[p].sum()) for p in PH],
    })
    phases["sous_total"] = phases["humain"] + phases["autres"]
    # 10 % arrondi à la centaine, total ramené au montant du cahier des charges (122 900 €)
    phases["provision"] = (phases["sous_total"] * PROVISION).round(-2).astype(int)
    phases.loc[phases.index[-1], "provision"] += PROVISION_TOTALE - phases["provision"].sum()
    phases["total"] = phases["sous_total"] + phases["provision"]
    return rh, autres, phases


def gantt(path: Path) -> None:
    lignes = []
    for ph in PHASES:
        ts = [t for t in TACHES if t[0] == ph]
        lignes.append((ph, PHASES[ph], min(D(t[2]) for t in ts), max(D(t[3]) for t in ts), True))
        lignes += [(ph, t[1], D(t[2]), D(t[3]), False) for t in ts]
    fig, ax = plt.subplots(figsize=(13, 9.5))
    for i, (ph, lib, d0, d1, est_phase) in enumerate(lignes):
        ax.barh(i, (d1 - d0).days + 1, left=mdates.date2num(d0), height=0.62 if est_phase else 0.42,
                color=COULEURS[ph], alpha=1 if est_phase else 0.45)
    ax.set_yticks(range(len(lignes)), [l[1] for l in lignes], fontsize=8.5)
    for t, est_phase in zip(ax.get_yticklabels(), [l[4] for l in lignes]):
        t.set_fontweight("bold" if est_phase else "normal")
    ax.invert_yaxis()
    for nom, j in JALONS:
        x = mdates.date2num(D(j))
        ax.axvline(x, color="black", lw=0.7, ls=":")
        ax.plot(x, -1.1, marker="D", color="black", ms=6, clip_on=False)
        ax.text(x, -1.7, nom, ha="center", fontsize=8)
    for _, s in sprints().iterrows():
        x0 = mdates.date2num(s["debut"])
        ax.text(x0 + 6, len(lignes) + 0.2, s["sprint"], ha="center", fontsize=7, color="#1f5f99")
        ax.axvspan(x0, x0 + 12, ymin=0, ymax=0.012, color="#1f5f99", alpha=0.35)
    ax.set_ylim(len(lignes) + 0.8, -2.3)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Projet Goutte d'eau – planning prévisionnel (novembre 2026 → novembre 2027)",
                 loc="left", fontsize=12, pad=28)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    rh, autres, phases = budget()
    pd.DataFrame([{"phase": t[0], "tache": t[1], "debut": t[2], "fin": t[3]} for t in TACHES]).to_csv(
        ICI / "planning.csv", index=False)
    sprints().to_csv(ICI / "sprints.csv", index=False)
    rh.to_csv(ICI / "budget_rh.csv", index=False)
    autres.to_csv(ICI / "budget_autres.csv", index=False)
    phases.to_csv(ICI / "budget_phases.csv", index=False)
    gantt(ICI / "gantt.png")
    mvp = sum(t * j for _, t, j in MVP)
    print(phases.to_string(index=False))
    print("Jours :", rh["jours"].sum(), "| humain :", rh["cout"].sum(), "| autres :", autres["cout"].sum(),
          "| provision :", phases["provision"].sum(), "| total :", phases["total"].sum(), "| MVP :", mvp)


if __name__ == "__main__":
    main()

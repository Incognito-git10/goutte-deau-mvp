"""Interface de démonstration du MVP Goutte d'eau.

Lancement : streamlit run app/streamlit_app.py
L'interface interroge l'API (GOUTTE_API_URL, défaut http://localhost:8000).
Si l'API ne répond pas, elle calcule la prévision en local avec le même service.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from goutte import config, prediction  # noqa: E402

API = os.getenv("GOUTTE_API_URL", "http://localhost:8000")
CLE = os.getenv("GOUTTE_API_KEY")

st.set_page_config(page_title="Goutte d'eau – risque de pluie", page_icon="💧", layout="centered")

# Libellés + pictogrammes : l'information ne repose jamais sur la seule couleur (RGAA 3.1)
NIVEAUX = {"faible": ("☀️", "Risque faible"), "modéré": ("🌥️", "Risque modéré"), "élevé": ("🌧️", "Risque élevé")}
st.markdown("""<style>
/* Focus clavier toujours visible (RGAA 10.7) */
:focus-visible { outline: 3px solid #1d4ed8 !important; outline-offset: 2px; }
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def appeler_api(jour: str, station: str | None) -> tuple[dict | None, str]:
    params = {"date": jour}
    if station:
        params["station_id"] = station
    try:
        r = requests.get(f"{API}/prevision", params=params, timeout=5,
                         headers={"X-API-Key": CLE} if CLE else {})
        if r.status_code == 404:
            return None, r.json().get("detail", "Date indisponible")
        r.raise_for_status()
        return r.json(), "api"
    except requests.RequestException:
        try:
            return prediction.predire_jour(date.fromisoformat(jour), station), "local"
        except prediction.DateIndisponible as e:
            return None, str(e)


st.title("💧 Goutte d'eau")
st.markdown(f"Probabilité de pluie dans les **{config.HORIZON_H} prochaines heures**, "
            f"heure par heure — région **{config.REGION}**.")

debut, fin = prediction.periode()
with st.form("recherche"):
    col1, col2 = st.columns(2)
    jour = col1.date_input("Date de la prévision", value=date.fromisoformat(fin),
                           min_value=date.fromisoformat(debut), max_value=date.fromisoformat(fin),
                           format="DD/MM/YYYY", help="Les données du MVP couvrent une période limitée.")
    options = {"": "Toute la région"} | {k: f"{v} ({k})" for k, v in config.STATIONS.items()}
    station = col2.selectbox("Station", list(options), format_func=options.get)
    envoye = st.form_submit_button("Calculer le risque", type="primary")

if envoye or "derniere" not in st.session_state:
    st.session_state["derniere"] = appeler_api(jour.isoformat(), station or None)

res, source = st.session_state["derniere"]
if res is None:
    st.warning(source)
    st.stop()

icone, libelle = NIVEAUX[res["niveau_journalier"]]
c1, c2, c3 = st.columns(3)
c1.metric("Niveau du jour", f"{icone} {libelle}")
c2.metric("Probabilité maximale", f"{res['risque_journalier']:.0%}")
c3.metric("Heures en alerte", len(res["heures_a_risque"]))

if res["heures_a_risque"]:
    st.info("Créneaux en alerte (heure de Paris) : " + ", ".join(res["heures_a_risque"]) +
            f". Une alerte signifie une probabilité supérieure à {res['seuil_decision']:.0%}, "
            "soit plusieurs fois le risque habituel.")
else:
    st.success("Aucun créneau en alerte sur la journée : fenêtre favorable aux traitements et travaux.")

df = pd.DataFrame(res["previsions_horaires"])
st.subheader("Évolution horaire")
st.line_chart(df.set_index("heure_locale")[["probabilite"]]
              .rename(columns={"probabilite": "Probabilité"}).assign(**{"Seuil d'alerte": res["seuil_decision"]}),
              y_label="Probabilité de pluie (0–1)", x_label="Heure de Paris")

# Alternative textuelle au graphique (lecteurs d'écran, RGAA 1.3)
with st.expander("Voir les données sous forme de tableau"):
    st.dataframe(df.rename(columns={"heure_locale": "Heure de Paris", "heure_utc": "Heure (UTC)",
                                    "probabilite": "Probabilité moyenne",
                                    "probabilite_max_station": "Probabilité max. station",
                                    "niveau": "Niveau", "stations": "Stations"}),
                 hide_index=True, use_container_width=True)

with st.expander("Qualité du modèle"):
    m = prediction.charger_metriques()
    e = m["evaluation"]
    st.markdown(
        f"- Modèle : **{m['modele_retenu']}**, seuil de décision {m['seuil_decision']}\n"
        f"- ROC-AUC : **{e['roc_auc']}** · PR-AUC : **{e['pr_auc']}**\n"
        f"- Rappel (pluies détectées) : **{e['rappel']:.0%}** · Précision : **{e['precision']:.0%}**\n"
        f"- Validation croisée par jour sur {m['jeu']['lignes']} heures-station, "
        f"{m['jeu']['jours_avec_pluie']} jours de pluie")

st.caption(f"Source : réseau Infoclimat (Licence Ouverte) · calcul : {'API' if source == 'api' else 'local'} · "
           "MVP France Météo – projet Goutte d'eau")

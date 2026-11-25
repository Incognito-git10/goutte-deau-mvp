"""API REST du MVP Goutte d'eau.

Lancement : uvicorn api.main:app --reload   (documentation interactive sur /docs)
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import Depends, FastAPI, HTTPException, Query, Security  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.security import APIKeyHeader  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from goutte import config, prediction  # noqa: E402

app = FastAPI(
    title="Goutte d'eau – API de prévision du risque de pluie",
    description="MVP France Météo : probabilité de pluie (≥ 0,2 mm) dans les 3 h, "
                f"heure par heure, pour la région {config.REGION}.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("GOUTTE_CORS", "http://localhost:8501").split(","),
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)

# Clé d'API facultative : si GOUTTE_API_KEY est définie, l'en-tête X-API-Key devient obligatoire
_cle = APIKeyHeader(name="X-API-Key", auto_error=False)


def verifier_cle(cle: str | None = Security(_cle)) -> None:
    attendue = os.getenv("GOUTTE_API_KEY")
    if attendue and cle != attendue:
        raise HTTPException(status_code=401, detail="Clé d'API invalide ou absente")


class PrevisionHoraire(BaseModel):
    heure_utc: str = Field(examples=["12:00"])
    heure_locale: str = Field(examples=["14:00"], description="Heure de Paris")
    probabilite: float = Field(ge=0, le=1, description="Probabilité moyenne sur les stations")
    probabilite_max_station: float = Field(ge=0, le=1)
    niveau: Literal["faible", "modéré", "élevé"]
    stations: int


class Prevision(BaseModel):
    date: str
    region: str
    station_id: str | None
    horizon_h: int
    risque_journalier: float = Field(ge=0, le=1)
    niveau_journalier: Literal["faible", "modéré", "élevé"]
    pluie_attendue: bool
    heures_a_risque: list[str] = Field(description="Heures locales où la probabilité dépasse le seuil d'alerte")
    seuil_decision: float
    modele: str
    previsions_horaires: list[PrevisionHoraire]


@app.middleware("http")
async def mesurer_latence(request, call_next):
    t0 = time.perf_counter()
    rep = await call_next(request)
    rep.headers["X-Temps-Traitement-ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
    return rep


@app.get("/", tags=["info"])
def accueil():
    return {"service": "goutte-deau", "version": app.version, "documentation": "/docs"}


@app.get("/sante", tags=["info"])
def sante():
    debut, fin = prediction.periode()
    return {"statut": "ok", "modele_charge": config.CHEMIN_MODELE.exists(),
            "donnees_du": debut, "donnees_au": fin}


@app.get("/stations", tags=["référentiel"], dependencies=[Depends(verifier_cle)])
def stations():
    return prediction.stations_disponibles()


@app.get("/prevision", response_model=Prevision, tags=["prévision"], dependencies=[Depends(verifier_cle)])
def prevision(
    date_prevision: date = Query(..., alias="date", description="Date au format AAAA-MM-JJ",
                                 examples=["2026-09-30"]),
    station_id: str | None = Query(None, max_length=12, pattern=r"^[A-Za-z0-9]+$",
                                   description="Restreindre à une station (facultatif)"),
):
    if station_id and station_id not in config.STATIONS:
        raise HTTPException(status_code=404, detail=f"Station inconnue : {station_id}")
    try:
        return prediction.predire_jour(date_prevision, station_id)
    except prediction.DateIndisponible as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/modele", tags=["qualité"], dependencies=[Depends(verifier_cle)])
def modele():
    m = prediction.charger_metriques()
    return {k: m[k] for k in ["modele_retenu", "seuil_decision", "horizon_h", "jeu",
                              "evaluation", "references", "test_temporel", "date_entrainement"]}

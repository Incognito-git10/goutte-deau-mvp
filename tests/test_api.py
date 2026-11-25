import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from goutte import config  # noqa: E402

pytestmark = pytest.mark.skipif(not config.CHEMIN_MODELE.exists(), reason="modèle non entraîné")


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


def test_sante(client):
    assert client.get("/sante").json()["statut"] == "ok"


def test_prevision_ok(client):
    r = client.get("/prevision", params={"date": "2026-09-30"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["niveau_journalier"] in {"faible", "modéré", "élevé"}
    assert "X-Temps-Traitement-ms" in r.headers


def test_prevision_date_invalide(client):
    assert client.get("/prevision", params={"date": "30/09/2026"}).status_code == 422


def test_prevision_hors_periode(client):
    assert client.get("/prevision", params={"date": "1999-01-01"}).status_code == 404


def test_station_inconnue(client):
    assert client.get("/prevision", params={"date": "2026-09-30", "station_id": "XXX"}).status_code == 404


def test_cle_api(client, monkeypatch):
    monkeypatch.setenv("GOUTTE_API_KEY", "secret")
    assert client.get("/stations").status_code == 401
    assert client.get("/stations", headers={"X-API-Key": "secret"}).status_code == 200

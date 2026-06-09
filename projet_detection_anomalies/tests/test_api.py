"""
Tests automatiques pour tous les endpoints de l'API.

Lancer les tests :
    pytest tests/ -v
Avec couverture :
    pytest tests/ -v --cov=api --cov-report=term-missing
"""

import io
import csv
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


PARAMS = {
    "seuil_operationnel": 0.302,
    "nb_feature": 44,
    "features": [f"feature_{i}" for i in range(44)],
    "architecture": "32→8→32",
    "epochs": 30,
    "batch_size": 256,
    "date_entrainement": "2026-05-12 10:34",
    "dataset": "dataset UNSW-NB15",
    "format_sortie": {"score_anomalie": "float MSE", "prediction": "0 ou 1", "seuil": "float"},
}

FLUX_NORMAL  = {"features": [0.0] * 44}
FLUX_ATTAQUE = {"features": [10.0] * 44}


@pytest.fixture(scope="module")
def client():
    pipeline_mock = MagicMock()
    pipeline_mock.transform.side_effect = lambda X: X.values if hasattr(X, "values") else X

    def score_mock(X):
        return np.array([float(np.mean(row ** 2)) for row in X])

    detecteur_mock = MagicMock()
    detecteur_mock.score_anomalie.side_effect = score_mock
    detecteur_mock.predict.side_effect = lambda X: (score_mock(X) > 0.302).astype(int)

    # On importe le module avec le vrai modèle, puis on remplace les vars module-level par les mocks.
    # Cela évite de devoir patcher avant l'import (charger_modele() est appelé à l'import).
    import api.app as app_module

    with patch.object(app_module, "pipeline",  pipeline_mock), \
         patch.object(app_module, "detecteur", detecteur_mock), \
         patch.object(app_module, "params",    PARAMS), \
         patch.object(app_module, "creer_table", lambda: None):
        with TestClient(app_module.app) as c:
            yield c


def _csv(nb_lignes: int, valeur: float = 0.0, avec_header: bool = False) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if avec_header:
        writer.writerow([f"feature_{i}" for i in range(44)])
    for _ in range(nb_lignes):
        writer.writerow([valeur] * 44)
    return buf.getvalue().encode("utf-8")


def _json(nb_lignes: int, valeur: float = 0.0) -> bytes:
    return json.dumps([[valeur] * 44 for _ in range(nb_lignes)]).encode("utf-8")


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestHealthCheck:

    def test_retourne_200(self, client):
        assert client.get("/").status_code == 200

    def test_status_est_ok(self, client):
        assert client.get("/").json()["status"] == "ok"

    def test_contient_les_champs_attendus(self, client):
        data = client.get("/").json()
        assert "status" in data and "modele" in data and "dataset" in data


# ── GET /info ─────────────────────────────────────────────────────────────────

class TestInfoModele:

    def test_retourne_200(self, client):
        assert client.get("/info").status_code == 200

    def test_nb_feature_est_44(self, client):
        assert client.get("/info").json()["nb_feature"] == 44

    def test_seuil_est_correct(self, client):
        assert client.get("/info").json()["seuil_operationnel"] == 0.302

    def test_architecture(self, client):
        assert client.get("/info").json()["architecture"] == "32→8→32"


# ── POST /predict ─────────────────────────────────────────────────────────────

class TestPredict:

    def test_flux_normal_retourne_200(self, client):
        assert client.post("/predict", json=FLUX_NORMAL).status_code == 200

    def test_flux_normal_classifie_normal(self, client):
        data = client.post("/predict", json=FLUX_NORMAL).json()
        assert data["prediction"] == 0 and data["is_anomalie"] is False

    def test_flux_attaque_classifie_attaque(self, client):
        data = client.post("/predict", json=FLUX_ATTAQUE).json()
        assert data["prediction"] == 1 and data["is_anomalie"] is True

    def test_score_attaque_superieur_au_normal(self, client):
        score_normal  = client.post("/predict", json=FLUX_NORMAL).json()["score_anomalie"]
        score_attaque = client.post("/predict", json=FLUX_ATTAQUE).json()["score_anomalie"]
        assert score_attaque > score_normal

    def test_severite_est_valide(self, client):
        assert client.post("/predict", json=FLUX_NORMAL).json()["severite"] in ("low", "medium", "high")

    def test_seuil_retourne(self, client):
        assert client.post("/predict", json=FLUX_NORMAL).json()["seuil_utilise"] == 0.302

    def test_score_est_float(self, client):
        assert isinstance(client.post("/predict", json=FLUX_NORMAL).json()["score_anomalie"], float)

    def test_prediction_est_0_ou_1(self, client):
        assert client.post("/predict", json=FLUX_NORMAL).json()["prediction"] in (0, 1)

    def test_trop_peu_features_retourne_422(self, client):
        assert client.post("/predict", json={"features": [0.0] * 10}).status_code == 422

    def test_trop_de_features_retourne_422(self, client):
        assert client.post("/predict", json={"features": [0.0] * 50}).status_code == 422

    def test_features_vides_retourne_422(self, client):
        assert client.post("/predict", json={"features": []}).status_code == 422


# ── POST /predict/batch ───────────────────────────────────────────────────────

class TestPredictBatch:

    def test_retourne_200(self, client):
        assert client.post("/predict/batch", json={"flux": [FLUX_NORMAL, FLUX_ATTAQUE]}).status_code == 200

    def test_nb_flux_correct(self, client):
        data = client.post("/predict/batch", json={"flux": [FLUX_NORMAL] * 5}).json()
        assert data["nb_flux"] == 5

    def test_nb_predictions_correct(self, client):
        data = client.post("/predict/batch", json={"flux": [FLUX_NORMAL, FLUX_ATTAQUE, FLUX_NORMAL]}).json()
        assert len(data["predictions"]) == 3

    def test_detecte_les_attaques(self, client):
        data = client.post("/predict/batch", json={"flux": [FLUX_NORMAL, FLUX_ATTAQUE]}).json()
        assert data["nb_attaques"] >= 1

    def test_batch_vide_retourne_422(self, client):
        assert client.post("/predict/batch", json={"flux": []}).status_code == 422

    def test_mauvais_nb_features_retourne_422(self, client):
        batch = {"flux": [FLUX_NORMAL, {"features": [0.0] * 10}]}
        assert client.post("/predict/batch", json=batch).status_code == 422

    def test_taux_attaques_calcul(self, client):
        batch = {"flux": [FLUX_NORMAL] * 3 + [FLUX_ATTAQUE]}
        data  = client.post("/predict/batch", json=batch).json()
        attendu = round(data["nb_attaques"] / data["nb_flux"] * 100, 2)
        assert data["taux_attaques"] == attendu

    def test_grand_batch(self, client):
        batch = {"flux": [FLUX_NORMAL] * 900 + [FLUX_ATTAQUE] * 100}
        response = client.post("/predict/batch", json=batch)
        assert response.status_code == 200
        assert response.json()["nb_flux"] == 1000


# ── POST /analyze ─────────────────────────────────────────────────────────────

class TestAnalyse:

    def test_csv_retourne_200(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.csv", _csv(5), "text/csv")}).status_code == 200

    def test_csv_nb_flux_correct(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(5), "text/csv")}).json()
        assert data["nb_flux_analyses"] == 5

    def test_csv_flux_normaux_aucune_attaque(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(3, valeur=0.0), "text/csv")}).json()
        assert data["nb_anomalies"] == 0

    def test_csv_flux_attaques_detectees(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(3, valeur=10.0), "text/csv")}).json()
        assert data["nb_anomalies"] > 0

    def test_csv_avec_header_ne_compte_pas(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(3, avec_header=True), "text/csv")}).json()
        assert data["nb_flux_analyses"] == 3

    def test_numerotation_commence_a_1(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(3), "text/csv")}).json()
        assert [r["ligne"] for r in data["resultats"]] == [1, 2, 3]

    def test_json_retourne_200(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.json", _json(5), "application/json")}).status_code == 200

    def test_format_non_supporte_retourne_422(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.txt", b"texte", "text/plain")}).status_code == 422

    def test_fichier_vide_retourne_422(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.csv", b"", "text/csv")}).status_code == 422

    def test_mauvais_nb_features_retourne_422(self, client):
        buf = io.StringIO()
        csv.writer(buf).writerow([0.0] * 10)
        assert client.post("/analyze", files={"fichier": ("logs.csv", buf.getvalue().encode(), "text/csv")}).status_code == 422

    def test_json_invalide_retourne_422(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.json", b"{json invalide", "application/json")}).status_code == 422

    def test_trop_de_lignes_retourne_422(self, client):
        assert client.post("/analyze", files={"fichier": ("logs.csv", _csv(10_001), "text/csv")}).status_code == 422

    def test_severite_valide_dans_resultats(self, client):
        data = client.post("/analyze", files={"fichier": ("logs.csv", _csv(3), "text/csv")}).json()
        for r in data["resultats"]:
            assert r["severite"] in ("low", "medium", "high")

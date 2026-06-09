"""
On veut vérifier automatiquement que chaque endpoint de la version 2 de l'API fonctionne correctement.
Ce fichier teste les nouveautés de main2.py : la sauvegarde automatique en BDD et l'historique avec filtres.

Pour lancer ces tests spécifiques : pytest test_api2.py -v
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock du modèle et des paramètres (simuler le comportement sans charger les vrais fichiers)
params = {
    "seuil_operationnel": 0.302,
    "nb_feature": 44,
    "features": [f"feature_{i}" for i in range(44)],
    "architecture": "32→8→32",
    "epochs": 30,
    "batch_size": 256,
    "date_entrainement": "2026-05-12 10:34",
    "dataset": "dataset UNSW-NB15",
    "format_sortie": {
        "score_anomalie": "flottant erreur MSE",
        "prediction": "un entier soit 0 pour normal ou 1 pour une attaque",
        "seuil": "flottant si score > seuil alors prediction vaut 1"
    }
}

# Flux simulés avec les nouveaux champs ip_source et type_attaque acceptés par main2.py
flux_normal = {"features": [0.0] * 44, "ip_source": "192.168.1.1", "type_attaque": None}
flux_attaque = {"features": [10.0] * 44, "ip_source": "10.0.0.5", "type_attaque": "DDoS"}

# Données de simulation pour la Base de Données SQLite (ce que get_anomalies doit renvoyer)
faux_historique_bdd = [
    {"id": 1, "date": "2026-05-19 14:00:00", "ip_source": "10.0.0.5", "type_attaque": "DDoS", "severite": "high", "score_anomalie": 12.5, "prediction": 1},
    {"id": 2, "date": "2026-05-19 14:05:00", "ip_source": "192.168.1.50", "type_attaque": "Exploits", "severite": "medium", "score_anomalie": 4.2, "prediction": 1}
]


@pytest.fixture(scope="module")  # fixture pour partager le client de test sans le recréer à chaque fois
def client():
    # 1. Mocks pour la partie IA (Pipeline et Détecteur)
    pipe_mock = MagicMock()
    pipe_mock.transform.side_effect = lambda X: X.values if hasattr(X, 'values') else X
    
    detecteur_mock = MagicMock()
    def score_anomalie_mock(X):
        return np.array([float(np.mean(row**2)) for row in X])
    detecteur_mock.score_anomalie.side_effect = score_anomalie_mock
    detecteur_mock.predict.side_effect = lambda X: (score_anomalie_mock(X) > 0.302).astype(int)

    # 2. Mocks pour database.py (Évite de toucher à la vraie base anomalies.db pendant les tests)
    sauvegarder_mock = MagicMock()
    get_anomalies_mock = MagicMock(return_value=(faux_historique_bdd, 2)) # Renvoie 2 fausses anomalies et un total de 2
    creer_table_mock = MagicMock()

    # Remplacement des composants réels de main2 par nos mocks temporaires
    with patch("main2.charger_modele", return_value=(pipe_mock, detecteur_mock, params)):
        with patch("main2.sauvegarder_anomalie", sauvegarder_mock), \
             patch("main2.get_anomalies", get_anomalies_mock), \
             patch("main2.creer_table", creer_table_mock), \
             patch("main2.pipe", pipe_mock), \
             patch("main2.detecteur", detecteur_mock), \
             patch("main2.params", params):
            
            from main2 import app  # Importation de la nouvelle API avec les mocks injectés
            with TestClient(app) as c:
                # On attache le mock de sauvegarde au client pour pouvoir l'inspecter dans les tests
                c.sauvegarder_mock = sauvegarder_mock
                yield c


# ==================== Tests Endpoint GET /anomalies ====================
# On vérifie que l'historique SQLite répond correctement, applique le bon format et gère les erreurs de sévérité.

class TestHistoriqueAnomalies:

    def test_status_ok_anomalies(self, client):
        response = client.get("/anomalies") # L'accès à l'historique doit retourner un code 200
        assert response.status_code == 200

    def test_champs_reponse_anomalies(self, client):
        data = client.get("/anomalies").json() # La réponse doit respecter le schéma Pydantic ReponseAnomalies
        assert "total" in data
        assert "page" in data
        assert "nb_pages" in data
        assert "limite" in data
        assert "anomalies" in data

    def test_structure_une_anomalie(self, client):
        data = client.get("/anomalies").json()
        premiere_anomalie = data["anomalies"][0]
        # Vérifie qu'une anomalie possède bien tous les champs configurés en base
        assert "id" in premiere_anomalie
        assert "date" in premiere_anomalie
        assert "ip_source" in premiere_anomalie
        assert "type_attaque" in premiere_anomalie
        assert "severite" in premiere_anomalie
        assert "score_anomalie" in premiere_anomalie
        assert "prediction" in premiere_anomalie

    def test_pagination_par_defaut(self, client):
        data = client.get("/anomalies").json()
        assert data["page"] == 1          # Par défaut la page courante est 1
        assert data["limite"] == 20       # Par défaut la limite est fixée à 20

    def test_validation_severite_incorrecte(self, client):
        response = client.get("/anomalies?severite=CRITIQUE") # "CRITIQUE" n'est pas low/medium/high -> Erreur 422 attendue
        assert response.status_code == 422
        assert "severite doit être" in response.json()["detail"]


# ==================== Tests Sauvegarde Automatique (Logique Métier) ====================
# On s'assure que l'API n'enregistre en base de données QUE lorsqu'une anomalie est détectée (prediction == 1).

class TestSauvegardeAutomatique:

    def test_predict_sauvegarde_si_attaque(self, client):
        client.sauvegarder_mock.reset_mock() # On remet le compteur du mock à zéro
        response = client.post("/predict", json=flux_attaque)
        assert response.status_code == 200
        # Un flux d'attaque doit déclencher AUTOMATIQUEMENT 1 sauvegarde en base de données
        assert client.sauvegarder_mock.call_count == 1

    def test_predict_ne_sauvegarde_pas_si_normal(self, client):
        client.sauvegarder_mock.reset_mock() # On remet le compteur du mock à zéro
        response = client.post("/predict", json=flux_normal)
        assert response.status_code == 200
        # Un flux normal ne doit JAMAIS être enregistré dans l'historique des anomalies (0 appel)
        assert client.sauvegarder_mock.call_count == 0

    def test_predict_batch_sauvegarde_uniquement_attaques(self, client):
        client.sauvegarder_mock.reset_mock()
        batch = {"flux": [flux_normal, flux_attaque, flux_normal]} # Batch contenant 1 seule attaque
        response = client.post("/predict/batch", json=batch)
        assert response.status_code == 200
        # Sur les 3 flux, seul le flux d'attaque doit être sauvegardé (1 appel attendu)
        assert client.sauvegarder_mock.call_count == 1
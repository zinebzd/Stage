"""
Tests automatiques pour tous les endpoints de lapi version 3.

A faire : 
pip install python-multipart
pytest test_api3.py -v

uvicorn main3:app --reload --port 8004
http://localhost:8004/docs
"""

import io
import csv
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# paramètres du modèle simulé
params = {
    "seuil_operationnel" : 0.302,
    "nb_feature"         : 44,
    "features"           : [f"feature_{i}" for i in range(44)],
    "architecture"       : "32→8→32",
    "epochs"             : 30,
    "batch_size"         : 256,
    "date_entrainement"  : "2026-05-12 10:34",
    "dataset"            : "dataset UNSW-NB15",
    "format_sortie"      : {
        "score_anomalie" : "flotant erreur mse",
        "prediction"     : "0 pour normal 1 pour attaque",
        "seuil"          : "flotant si score > seuil alors prediction vaut 1"
    }
}

flux_normal  = {"features": [0.0] * 44}   
flux_attaque = {"features": [10.0] * 44}  

@pytest.fixture(scope="module")
def client():
    pipe_mock = MagicMock()
    pipe_mock.transform.side_effect = lambda X: X.values if hasattr(X, "values") else X
    detecteur_mock = MagicMock()
    def score_anomalie_mock(X):
        return np.array([float(np.mean(row**2)) for row in X])
    detecteur_mock.score_anomalie.side_effect = score_anomalie_mock
    detecteur_mock.predict.side_effect = lambda X: (score_anomalie_mock(X) > 0.302).astype(int)
    with patch("main3.charger_modele", return_value=(pipe_mock, detecteur_mock, params)):     # remplace les vrais objets de main3.py par les mocks le temps des tests
        with patch("main3.pipe", pipe_mock), \
             patch("main3.detecteur", detecteur_mock), \
             patch("main3.params", params), \
             patch("main3.creer_table"):  # évite de créer une vraie base sqlite pendant les tests
            from main3 import app
            with TestClient(app) as c:
                yield c


# fonctions utilitaires pour créer des fichiers de test

#  crée un fichier csv en mémoire avec nb_lignes lignes de 44 features
def creer_csv(nb_lignes: int, valeur: float = 0.0, avec_header: bool = False) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    if avec_header:
        writer.writerow([f"feature_{i}" for i in range(44)])  # en-tête optionnel
    for _ in range(nb_lignes):
        writer.writerow([valeur] * 44)
    return output.getvalue().encode("utf-8")

# crée un fichier json en mémoire avec nb_lignes listes de 44 features
def creer_json(nb_lignes: int, valeur: float = 0.0) -> bytes:
    donnees = [[valeur] * 44 for _ in range(nb_lignes)]
    return json.dumps(donnees).encode("utf-8")


# tests endpoint GET /

class TestHealthCheck:

    def test_status_ok(self, client):
        assert client.get("/").status_code == 200

    def test_contenu_reponse(self, client):
        data = client.get("/").json()
        assert "status"  in data
        assert "modele"  in data
        assert "dataset" in data

    def test_status_value(self, client):
        assert client.get("/").json()["status"] == "ok"

    def test_dataset_unsw(self, client):
        assert client.get("/").json()["dataset"] == "dataset UNSW-NB15"


# tests endpoint GET /info

class TestInfoModele:

    def test_status_ok(self, client):
        assert client.get("/info").status_code == 200

    def test_champs_obligatoires(self, client):
        data = client.get("/info").json()
        assert "architecture"       in data
        assert "nb_feature"         in data
        assert "seuil_operationnel" in data
        assert "date_entrainement"  in data
        assert "dataset"            in data
        assert "format_sortie"      in data

    def test_nb_feature(self, client):
        assert client.get("/info").json()["nb_feature"] == 44

    def test_seuil(self, client):
        assert client.get("/info").json()["seuil_operationnel"] == 0.302

    def test_architecture(self, client):
        assert client.get("/info").json()["architecture"] == "32→8→32"


# tests endpoint POST /predict

class TestPredict:

    def test_status_ok_flux_normal(self, client):
        assert client.post("/predict", json=flux_normal).status_code == 200

    def test_champs_reponse(self, client):
        data = client.post("/predict", json=flux_normal).json()
        assert "score_anomalie" in data
        assert "prediction"     in data
        assert "is_anomalie"    in data
        assert "severite"       in data
        assert "seuil_utilise"  in data

    def test_flux_normal_classifie_normal(self, client):
        data = client.post("/predict", json=flux_normal).json()
        assert data["prediction"]  == 0
        assert data["is_anomalie"] == False

    def test_flux_attaque_classifie_attaque(self, client):
        data = client.post("/predict", json=flux_attaque).json()
        assert data["prediction"]  == 1
        assert data["is_anomalie"] == True

    def test_score_attaque_superieur_normal(self, client):
        score_normal  = client.post("/predict", json=flux_normal).json()["score_anomalie"]
        score_attaque = client.post("/predict", json=flux_attaque).json()["score_anomalie"]
        assert score_attaque > score_normal

    def test_seuil_retourne(self, client):
        assert client.post("/predict", json=flux_normal).json()["seuil_utilise"] == 0.302

    def test_trop_peu_features(self, client):
        assert client.post("/predict", json={"features": [0.0] * 10}).status_code == 422

    def test_trop_de_features(self, client):
        assert client.post("/predict", json={"features": [0.0] * 50}).status_code == 422

    def test_features_vides(self, client):
        assert client.post("/predict", json={"features": []}).status_code == 422

    def test_score_est_float(self, client):
        assert isinstance(client.post("/predict", json=flux_normal).json()["score_anomalie"], float)

    def test_prediction_est_0_ou_1(self, client):
        assert client.post("/predict", json=flux_normal).json()["prediction"] in [0, 1]

    def test_severite_valide(self, client):
        severite = client.post("/predict", json=flux_normal).json()["severite"]
        assert severite in ["low", "medium", "high"]


# tests endpoint POST /predict/batch

class TestPredictBatch:

    def test_status_ok(self, client):
        assert client.post("/predict/batch", json={"flux": [flux_normal, flux_attaque]}).status_code == 200

    def test_champs_reponse(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal]}).json()
        assert "nb_flux"       in data
        assert "nb_attaques"   in data
        assert "taux_attaques" in data
        assert "predictions"   in data

    def test_nb_flux_correct(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal] * 5}).json()
        assert data["nb_flux"] == 5

    def test_nb_predictions_correct(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal, flux_attaque, flux_normal]}).json()
        assert len(data["predictions"]) == 3

    def test_batch_vide(self, client):
        assert client.post("/predict/batch", json={"flux": []}).status_code == 422

    def test_detection_attaque_dans_batch(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal, flux_attaque]}).json()
        assert data["nb_attaques"] >= 1

    def test_taux_attaques_calcul(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal] * 3 + [flux_attaque]}).json()
        taux_attendu = round(data["nb_attaques"] / data["nb_flux"] * 100, 2)
        assert data["taux_attaques"] == taux_attendu

    def test_batch_features_incorrectes(self, client):
        batch = {"flux": [flux_normal, {"features": [0.0] * 10}]}
        assert client.post("/predict/batch", json=batch).status_code == 422

    def test_grand_batch(self, client):
        batch = {"flux": [flux_normal] * 900 + [flux_attaque] * 100}
        response = client.post("/predict/batch", json=batch)
        assert response.status_code == 200
        assert response.json()["nb_flux"] == 1000


# tests endpoint POST /analyze 

class TestAnalyse:

    # tests avec fichier csv 
    def test_csv_status_ok(self, client):          # un csv valide avec des flux normaux doit retourner 200
        fichier = creer_csv(5)
        response = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")})
        assert response.status_code == 200

    def test_csv_champs_reponse(self, client):         # la réponse doit contenir les 4 champs attendus
        fichier = creer_csv(3)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert "nb_flux_analyses" in data
        assert "nb_anomalies"     in data
        assert "taux_anomalies"   in data
        assert "resultats"        in data

    def test_csv_nb_flux_correct(self, client):         # on envoie 5 lignes donc on doit recevoir 5 résultats
        fichier = creer_csv(5)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert data["nb_flux_analyses"] == 5
        assert len(data["resultats"])   == 5

    def test_csv_flux_normaux(self, client):         # un csv avec des features à 0 ne doit détecter aucune attaque
        fichier = creer_csv(3, valeur=0.0)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert data["nb_anomalies"] == 0

    def test_csv_flux_attaques(self, client):         # un csv avec des features à 10 doit détecter des attaques
        fichier = creer_csv(3, valeur=10.0)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert data["nb_anomalies"] > 0

    def test_csv_avec_header(self, client):         # un csv avec une ligne d'en-tête doit être correctement ignoré
        fichier = creer_csv(3, avec_header=True)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert data["nb_flux_analyses"] == 3  # len-tête ne compte pas

    def test_csv_numerotation_lignes(self, client):         # les numéros de lignes doivent commencer à 1
        fichier = creer_csv(3)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        lignes = [r["ligne"] for r in data["resultats"]]
        assert lignes == [1, 2, 3]

    # tests avec fichier json 
    def test_json_status_ok(self, client):         # un json valide doit retourner 200
        fichier = creer_json(5)
        response = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")})
        assert response.status_code == 200

    def test_json_nb_flux_correct(self, client):         # on envoie 4 éléments donc on doit recevoir 4 résultats
        fichier = creer_json(4)
        data = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")}).json()
        assert data["nb_flux_analyses"] == 4

    def test_json_flux_normaux(self, client):
        fichier = creer_json(3, valeur=0.0)
        data = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")}).json()
        assert data["nb_anomalies"] == 0

    def test_json_flux_attaques(self, client):
        fichier = creer_json(3, valeur=10.0)
        data = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")}).json()
        assert data["nb_anomalies"] > 0

    #  tests de validation des erreurs 

    def test_format_non_supporte(self, client):         # un fichier txt doit être rejeté avec une erreur 422
        fichier = b"Ce ficher n'est pas au format csv"
        response = client.post("/analyze", files={"fichier": ("logs.txt", fichier, "text/plain")})
        assert response.status_code == 422

    def test_fichier_vide(self, client):        # un fichier vide doit retourner une erreur 422
        response = client.post("/analyze", files={"fichier": ("logs.csv", b"", "text/csv")})
        assert response.status_code == 422

    def test_csv_mauvais_nombre_features(self, client):         # un csv avec 10 colonnes au lieu de 44 doit retourner 422
        output = io.StringIO()
        csv.writer(output).writerow([0.0] * 10)
        fichier = output.getvalue().encode("utf-8")
        response = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")})
        assert response.status_code == 422

    def test_csv_valeurs_non_numeriques(self, client):         # un csv avec du texte dans les données doit retourner 422
        ligne_valide = ",".join(["0.0"] * 44)         # on met dabord une ligne valide pour ne pas quelle soit prise comme en-tête
        ligne_invalide = ",".join(["abc"] * 44)         # puis une ligne avec du texte au milieu des données
        fichier = f"{ligne_valide}\n{ligne_invalide}\n".encode("utf-8")
        response = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")})
        assert response.status_code == 422



    def test_json_invalide(self, client):         # du json malformé doit retourner 422
        fichier = b"{ceci nest pas du json valide"
        response = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")})
        assert response.status_code == 422

    def test_json_pas_une_liste(self, client):         # un json qui nest pas une liste doit retourner 422
        fichier = json.dumps({"key": "value"}).encode("utf-8")
        response = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")})
        assert response.status_code == 422

    def test_json_mauvais_nombre_features(self, client):         # un json avec des listes de 10 éléments au lieu de 44 doit retourner 422
        fichier = json.dumps([[0.0] * 10]).encode("utf-8")
        response = client.post("/analyze", files={"fichier": ("logs.json", fichier, "application/json")})
        assert response.status_code == 422

    def test_trop_de_lignes(self, client):         # un fichier avec plus de 10000 lignes doit être rejeté
        fichier = creer_csv(10001)
        response = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")})
        assert response.status_code == 422

    #  tests sur le contenu des résultats 

    def test_champs_resultat_analyse(self, client):         # chaque résultat doit contenir les 6 champs attendus
        fichier = creer_csv(1)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        r = data["resultats"][0]
        assert "ligne"          in r
        assert "score_anomalie" in r
        assert "prediction"     in r
        assert "is_anomalie"    in r
        assert "severite"       in r
        assert "seuil_utilise"  in r

    def test_severite_valide_dans_resultats(self, client):         # la sévérité de chaque résultat doit être low medium ou high
        fichier = creer_csv(5)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        for r in data["resultats"]:
            assert r["severite"] in ["low", "medium", "high"]

    def test_taux_anomalies_calcul(self, client):
        fichier = creer_csv(4, valeur=10.0)  
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        taux_attendu = round(data["nb_anomalies"] / data["nb_flux_analyses"] * 100, 2)
        assert data["taux_anomalies"] == taux_attendu

    def test_score_est_float(self, client):
        fichier = creer_csv(1)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        assert isinstance(data["resultats"][0]["score_anomalie"], float)

    def test_prediction_est_0_ou_1(self, client):
        fichier = creer_csv(3)
        data = client.post("/analyze", files={"fichier": ("logs.csv", fichier, "text/csv")}).json()
        for r in data["resultats"]:
            assert r["prediction"] in [0, 1]

"""
On veut vérifier automatiquement que chaque endpoint de l'API fonctionne correctement.
 Au lieu de tester manuellement depuis le navigateur, pytest lance tous les tests d'un coup et dit si quelque chose fonctionne mal.

Pour lancer les tests :pytest tests/ -v

Pour lancer avec le rapport de couverture :pytest tests/ -v --cov=main --cov-report=term-missing
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock du modèle (simuler quelque chose de faux qui se comporte comme le vrai) pour ne pas charger le vrai modèle pendant les tests
# On simule le comportement du modèle sans avoir besoin des fichiers sauvegardés

params = {"seuil_operationnel" : 0.302,"nb_feature" : 44,"features" : [f"feature_{i}" for i in range(44)],"architecture"  : "32→8→32","epochs" : 30, "batch_size" : 256,"date_entrainement"  : "2026-05-12 10:34",
    "dataset"  : "dataset UNSW-NB15","format_sortie" : {"score_anomalie" : "fltant erreur MSE","prediction" : "un entier soit 0 pour normal ou 1 pour une attaque","seuil": "flotant si score > seuil alors prediction vaut 1" }}

# flux normal simulé (44 features à 0 → bien reconstruit → score faible)
flux_normal  = {"features": [0.0] * 44}
# flux attaque simulé (44 features à 10 → mal reconstruit → score élevé)
flux_attaque = {"features": [10.0] * 44}


#Les points clés crés ici sont : 
#fixture qui est une ressource créée une fois et partagée avec tous les tests afin d'évite' de recréer le client 25 fois.
#MagicMock() est un objet qui accepte n'importe quel appel sans planter et on lui greffe ensuite le comportement qu'on veut avec side_effect.
#patch() remplace temporairement les vrais objets de main.py par les faux le temps des tests, puis remet les vrais à la fin automatiquement.
#yield c  donne le client au test, attend que le test finisse, puis nettoie.


@pytest.fixture(scope="module")  # fixture est une ressource partagée entre tous les tests, créée une seule fois
def client():
    pipe_mock = MagicMock()  # crée un faux objet qui imite le vrai pipe
    pipe_mock.transform.side_effect = lambda X: X.values if hasattr(X, 'values') else X    # .transform() retourne les valeurs numpy du DataFrame sans vraiment normaliser
    detecteur_mock = MagicMock()  # crée un faux détecteur

    def score_anomalie_mock(X): # simule le score MSE  si features=0 alors score=0 donc normal mais si features=10 alors score=100 donc attaque
        return np.array([float(np.mean(row**2)) for row in X])
    detecteur_mock.score_anomalie.side_effect = score_anomalie_mock     # quand on appelle score_anomalie() alors utilise notre fonction simulée
    detecteur_mock.predict.side_effect = lambda X: (score_anomalie_mock(X) > 0.302).astype(int)     # quand on appelle predict() alors si score > 0.302 c'est une attaque, sinon normal

    # remplacement du vrai modèle par les mocks
    # patch() remplace temporairement les vrais objets dans main.py par les faux
    with patch("main.charger_modele", return_value=(pipe_mock, detecteur_mock, params)):
        with patch("main.pipe",  pipe_mock), \
             patch("main.detecteur", detecteur_mock), \
             patch("main.params",    params):
            from main import app          # importe l'API avec les mocks actifs
            with TestClient(app) as c:   # crée un client HTTP de test
                yield c                  # donne le client à chaque test qui en a besoin


# Tests Endpoints GET /
# On veut vérifier que l'endpoint GET / fonctionne correctement , qu'il répond, qu'il retourne les bonnes données et les bonnes valeurs.

class TestHealthCheck: # 4 tests pour l'endpoint GET /

    def test_status_ok(self, client):   # envoie une requête GET sur "/"
        response = client.get("/")
        assert response.status_code == 200         # vérifie que l'API répond avec un code 200 donc succès

    def test_contenu_reponse(self, client):
        response = client.get("/")
        data = response.json()  # convertit la réponse json en dict Python
        # vérifie que les 4 champs attendus sont bien présents dans la réponse
        assert "status"  in data
        assert "message" in data
        assert "modele"  in data
        assert "dataset" in data

    def test_status_value(self, client):
        response = client.get("/")
        assert response.json()["status"] == "ok"        # vérifie que la valeur de "status" est bien "ok" 

    def test_dataset_unsw(self, client):
        response = client.get("/")
        assert response.json()["dataset"] == "dataset UNSW-NB15"         # vérifie que le dataset retourné est bien UNSW-NB15



# Test endpoint GET /info
# On veut vérifier que l'endpoint GET /info retourne bien toutes les informations du modèle avec les bonnes valeurs.

class TestInfoModele:
    
    def test_status_ok(self, client):
        assert client.get("/info").status_code == 200        # vérifie que l'endpoint répond sans erreur
 
    def test_champs_obligatoires(self, client):
        data = client.get("/info").json()         # vérifie que tous les champs du modèle sont présents dans la réponse
        assert "architecture"       in data
        assert "nb_feature"        in data
        assert "seuil_operationnel" in data
        assert "date_entrainement"  in data
        assert "dataset"            in data
        assert "format_sortie"      in data

    def test_nb_feature(self, client):
        data = client.get("/info").json()
        assert data["nb_feature"] == 44         # vérifie que le modèle attend bien 44 features en entrée

    def test_seuil(self, client):
        data = client.get("/info").json()
        assert data["seuil_operationnel"] == 0.302         # vérifie que le seuil opérationnel retenu est bien 0.302

    def test_architecture(self, client):
        data = client.get("/info").json() 
        assert data["architecture"] == "32→8→32"         # vérifie que l'architecture de l'autoencoder est bien 32→8→32




# Tests endpoints POST /predict
#Tests pour l'endpoint POST /predict (prédiction sur un flux).

class TestPredict:

    def test_status_ok_flux_normal(self, client):
        response = client.post("/predict", json=flux_normal) # un flux normal doit retourner un code 200
        assert response.status_code == 200

    def test_champs_reponse(self, client): # la réponse doit contenir les 4 champs attendus
        data = client.post("/predict", json=flux_normal).json()
        assert "score_anomalie" in data
        assert "prediction"     in data
        assert "is_anomalie"    in data
        assert "seuil_utilise"  in data

    def test_flux_normal_classifie_normal(self, client): #Un flux avec toutes les features à 0 doit être classé normal
        data = client.post("/predict", json=flux_normal).json()
        assert data["prediction"]  == 0
        assert data["is_anomalie"] == False

    def test_flux_attaque_classifie_attaque(self, client): # un flux avec toutes les features à 10 doit être classé attaque
        data = client.post("/predict", json=flux_attaque).json()
        assert data["prediction"]  == 1
        assert data["is_anomalie"] == True

    def test_score_attaque_superieur_normal(self, client): #le score d'une attaque doit être supérieur à celui d'un flux normal
        score_normal  = client.post("/predict", json=flux_normal).json()["score_anomalie"]
        score_attaque = client.post("/predict", json=flux_attaque).json()["score_anomalie"]
        assert score_attaque > score_normal

    def test_seuil_retourne(self, client): # le seuil retourné doit être le seuil opérationnel 0.302
        data = client.post("/predict", json=flux_normal).json()
        assert data["seuil_utilise"] == 0.302

    def test_trop_peu_features(self, client): # Un flux avec moins de 44 features doit retourner une erreur 422
        flux_incomplet = {"features": [0.0] * 10}
        response = client.post("/predict", json=flux_incomplet)
        assert response.status_code == 422

    def test_trop_de_features(self, client): #un flux avec plus de 44 features doit retourner une erreur 422
        flux_trop_grand = {"features": [0.0] * 50}
        response = client.post("/predict", json=flux_trop_grand)
        assert response.status_code == 422

    def test_features_vides(self, client): #un flux sans features doit retourner une erreur
        response = client.post("/predict", json={"features": []})
        assert response.status_code == 422

    def test_score_est_float(self, client): #le score d'anomalie doit être un nombre flottant
        data = client.post("/predict", json=flux_normal).json()
        assert isinstance(data["score_anomalie"], float)

    def test_prediction_est_0_ou_1(self, client): # la prédiction doit être exactement 0 ou 1
        data = client.post("/predict", json=flux_normal).json()
        assert data["prediction"] in [0, 1]


#Tests endpoints POST /predict/batch
# On vérifie que l'endpoint POST /predict/batch gère correctement plusieurs flux à la fois soient bonne taille, bon taux, erreurs bien rejetées

class TestPredictBatch:
    
    def test_status_ok(self, client):    # un batch avec un normal et une attaque doit répondre 200
        batch = {"flux": [flux_normal, flux_attaque]}
        assert client.post("/predict/batch", json=batch).status_code == 200

    def test_champs_reponse(self, client):
        data = client.post("/predict/batch", json={"flux": [flux_normal]}).json()         # vérifie que les 4 champs du batch sont présents
        assert "nb_flux"       in data
        assert "nb_attaques"   in data
        assert "taux_attaques" in data
        assert "predictions"   in data

    def test_nb_flux_correct(self, client):
        batch = {"flux": [flux_normal] * 5}
        data  = client.post("/predict/batch", json=batch).json()
        assert data["nb_flux"] == 5         # on envoie 5 flux donc on doit recevoir 5 en retour

    def test_nb_predictions_correct(self, client):
        batch = {"flux": [flux_normal, flux_attaque, flux_normal]}
        data  = client.post("/predict/batch", json=batch).json()
        assert len(data["predictions"]) == 3      # 3 flux envoyés donc 3 prédictions détaillées en retour

    def test_batch_vide(self, client):
        assert client.post("/predict/batch", json={"flux": []}).status_code == 422         # un batch sans flux doit être rejeté avec une erreur 422

    def test_detection_attaque_dans_batch(self, client):
        batch = {"flux": [flux_normal, flux_attaque]}
        data  = client.post("/predict/batch", json=batch).json()
        assert data["nb_attaques"] >= 1         # l'attaque dans le batch doit être détectée

    def test_taux_attaques_calcul(self, client):
        batch = {"flux": [flux_normal] * 3 + [flux_attaque] * 1}
        data  = client.post("/predict/batch", json=batch).json()        # vérifie que le taux = nb_attaques / nb_flux * 100
        taux_attendu = round(data["nb_attaques"] / data["nb_flux"] * 100, 2) 
        assert data["taux_attaques"] == taux_attendu

    def test_batch_features_incorrectes(self, client):
        batch = {"flux": [flux_normal, {"features": [0.0] * 10}]}         # un flux avec 10 features au lieu de 44 dans un batch doit retourner 422
        assert client.post("/predict/batch", json=batch).status_code == 422

    def test_grand_batch(self, client):
        batch = {"flux": [flux_normal] * 900 + [flux_attaque] * 100}         # 1000 flux d'un coup doivent être traités sans erreur
        response = client.post("/predict/batch", json=batch)
        assert response.status_code == 200
        assert response.json()["nb_flux"] == 1000  # on vérifie que tous les flux ont été traités
"""
Description : Simuler un flux de nouveaux logs (batch). Vérifier que le pipeline produit des résultats cohérents. Tester la robustesse avec des données bruitées ou incomplètes.
Ce fichier ne réentraîne pas le modèle, il utilise le modèle sauvegardé.

- Avoir exécuté models/serialiser_modele.py pour générer modele_sauvegarde/
    pytest tests/test_pipeline.py -v
"""

import json
import joblib
import numpy as np
import pandas as pd
from tensorflow import keras
from models.pipeline import AutoencoderDetecteur


dossier = "modele_sauvegarde"


def charger():
    with open(f"{dossier}/parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)
    pipeline = joblib.load(f"{dossier}/pipeline_sklearn.joblib")
    detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(f"{dossier}/autoencoder.keras")
    return pipeline, detecteur, params


def generer_batch(n_normal: int, n_attaque: int, nb_features: int, seed=42):
    rng = np.random.default_rng(seed)
    X_normal = rng.normal(loc=0.0, scale=0.5, size=(n_normal, nb_features))
    X_attaque = rng.normal(loc=3.0, scale=2.0, size=(n_attaque, nb_features))
    X = np.vstack([X_normal, X_attaque])
    y = np.array([0] * n_normal + [1] * n_attaque)
    idx = rng.permutation(len(X))
    return X[idx], y[idx]



def test_batch(pipeline, detecteur, params):
    nb_features = params["nb_features"]
    for taille, n_attaque in [(100, 10), (1000, 50), (10000, 500)]:
        X, y = generer_batch(taille - n_attaque, n_attaque, nb_features)
        scores = detecteur.score_anomalie(X)
        predictions = detecteur.predict(X)

        tp = ((predictions == 1) & (y == 1)).sum()
        fp = ((predictions == 1) & (y == 0)).sum()
        print(f"\n[Batch {taille} flux | {n_attaque} attaques]")
        print(f"  Score moyen normaux  : {scores[y==0].mean():.4f}")
        print(f"  Score moyen attaques : {scores[y==1].mean():.4f}")
        print(f"  Détectées : {tp} | Fausses alertes : {fp}")

    print("\nTest 1 le pipeline traite correctement les batchs")




def test_coherence(pipeline, detecteur, params):
    nb_features = params["nb_features"]

    X_normal = np.zeros((10, nb_features))       # flux parfaitement normal 
    X_attaque = np.ones((10, nb_features)) * 10  # flux très anormal

    scores_normal = detecteur.score_anomalie(X_normal)
    scores_attaque = detecteur.score_anomalie(X_attaque)
    preds_normal = detecteur.predict(X_normal)
    preds_attaque = detecteur.predict(X_attaque)

    print(f"\nScore flux normal  : {scores_normal.mean():.4f} → prédictions : {preds_normal.tolist()}")
    print(f"Score flux attaque : {scores_attaque.mean():.4f} → prédictions : {preds_attaque.tolist()}")

    assert scores_attaque.mean() > scores_normal.mean(), "Les attaques devraient avoir un score plus élevé"
    assert all(preds_normal == 0), "Les flux normaux devraient tous être classés 0"
    assert all(preds_attaque == 1), "Les flux anormaux devraient tous être classés 1"

    print("Test 2 le modèle est cohérent")



def test_robustesse(pipeline, detecteur, params):
    nb_features = params["nb_features"]
    features = params["features"]

    cas_difficiles = {
        "50% de NaN": pd.DataFrame(
            np.where(np.random.rand(100, nb_features) < 0.5, np.nan, np.random.normal(0, 1, (100, nb_features))),
            columns=features,
        ),
        "Valeurs infinies": pd.DataFrame(
            np.random.choice([np.inf, -np.inf], size=(100, nb_features)),
            columns=features,
        ),
        "Tout à zéro": pd.DataFrame(np.zeros((100, nb_features)), columns=features),
        "Outliers extrêmes": pd.DataFrame(np.random.normal(0, 1000, (100, nb_features)), columns=features),
        "Mix NaN + inf": pd.DataFrame(
            np.where(np.random.rand(100, nb_features) < 0.2, np.nan,
            np.where(np.random.rand(100, nb_features) < 0.1, np.inf,
            np.random.normal(0, 1, (100, nb_features)))),
            columns=features,
        ),
    }

    for nom, X in cas_difficiles.items():
        try:
            X_normalise = pipeline.transform(X)
            scores = detecteur.score_anomalie(X_normalise)
            predictions = detecteur.predict(X_normalise)
            print(f"\n[{nom}] Score moy : {scores.mean():.4f} et Attaques : {predictions.sum()}/100")
        except Exception as e:
            print(f"\n[{nom}] ERREUR : {e}")

    print("\nTest 3 le pipeline est robuste face aux données corrompues")



if __name__ == "__main__":
    pipeline, detecteur, params = charger()
    print(f"Modèle chargé avec un seuil : {params['seuil_operationnel']} et features : {params['nb_features']}")

    test_batch(pipeline, detecteur, params)
    test_coherence(pipeline, detecteur, params)
    test_robustesse(pipeline, detecteur, params)
    print("\nTous les tests ont réussi.")

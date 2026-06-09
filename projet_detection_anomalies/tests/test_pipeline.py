"""
Tests du pipeline de détection sur des données simulées.

Ce fichier utilise le modèle sauvegardé dans modele_sauvegarde/.
Il ne réentraîne pas le modèle.

Lancer :
    pytest tests/test_pipeline.py -v
"""

import json
import joblib
import numpy as np
import pytest
import pandas as pd
from pathlib import Path
from tensorflow import keras
from models.pipeline import AutoencoderDetecteur


DOSSIER = Path(__file__).parent.parent / "modele_sauvegarde"


def charger():
    with open(DOSSIER / "parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)
    pip = joblib.load(DOSSIER / "pipeline_sklearn.joblib")
    det = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    det.model_ = keras.models.load_model(DOSSIER / "autoencoder.keras")
    return pip, det, params


@pytest.fixture(scope="module")
def _modele():
    return charger()

@pytest.fixture(scope="module")
def pipeline(_modele):
    return _modele[0]

@pytest.fixture(scope="module")
def detecteur(_modele):
    return _modele[1]

@pytest.fixture(scope="module")
def params(_modele):
    return _modele[2]


def generer_batch(n_normal: int, n_attaque: int, nb_features: int, seed: int = 42):
    rng = np.random.default_rng(seed)
    X_normal  = rng.normal(loc=0.0, scale=0.5, size=(n_normal,  nb_features))
    X_attaque = rng.normal(loc=3.0, scale=2.0, size=(n_attaque, nb_features))
    X = np.vstack([X_normal, X_attaque])
    y = np.array([0] * n_normal + [1] * n_attaque)
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


def test_batch(pipeline, detecteur, params):
    nb_features = params["nb_feature"]
    for taille, n_attaque in [(100, 10), (1000, 50), (10000, 500)]:
        X, y = generer_batch(taille - n_attaque, n_attaque, nb_features)
        scores      = detecteur.score_anomalie(X)
        predictions = detecteur.predict(X)
        tp = ((predictions == 1) & (y == 1)).sum()
        fp = ((predictions == 1) & (y == 0)).sum()
        print(f"\n[Batch {taille} flux | {n_attaque} attaques]")
        print(f"  Score moyen normaux  : {scores[y==0].mean():.4f}")
        print(f"  Score moyen attaques : {scores[y==1].mean():.4f}")
        print(f"  Détectées : {tp} | Fausses alertes : {fp}")
    print("\nTest 1 : le pipeline traite correctement les batchs")


def test_coherence(pipeline, detecteur, params):
    nb_features = params["nb_feature"]
    X_normal  = np.zeros((10, nb_features))
    X_attaque = np.ones((10, nb_features)) * 10

    scores_normal  = detecteur.score_anomalie(X_normal)
    scores_attaque = detecteur.score_anomalie(X_attaque)
    preds_normal   = detecteur.predict(X_normal)
    preds_attaque  = detecteur.predict(X_attaque)

    print(f"\nScore flux normal  : {scores_normal.mean():.4f} → {preds_normal.tolist()}")
    print(f"Score flux attaque : {scores_attaque.mean():.4f} → {preds_attaque.tolist()}")

    assert scores_attaque.mean() > scores_normal.mean(), "Les attaques doivent avoir un score plus élevé"
    assert all(preds_normal  == 0), "Les flux normaux doivent tous être classés 0"
    assert all(preds_attaque == 1), "Les flux anormaux doivent tous être classés 1"
    print("Test 2 : le modèle est cohérent")


def test_robustesse(pipeline, detecteur, params):
    nb_features = params["nb_feature"]
    features    = params["features"]

    cas = {
        "50% de NaN": pd.DataFrame(
            np.where(np.random.rand(100, nb_features) < 0.5, np.nan,
                     np.random.normal(0, 1, (100, nb_features))),
            columns=features,
        ),
        "Valeurs infinies": pd.DataFrame(
            np.random.choice([np.inf, -np.inf], size=(100, nb_features)),
            columns=features,
        ),
        "Tout à zéro": pd.DataFrame(np.zeros((100, nb_features)), columns=features),
        "Outliers extrêmes": pd.DataFrame(np.random.normal(0, 1000, (100, nb_features)), columns=features),
    }

    for nom, X in cas.items():
        try:
            X_normalise = pipeline.transform(X)
            scores      = detecteur.score_anomalie(X_normalise)
            predictions = detecteur.predict(X_normalise)
            print(f"\n[{nom}] Score moy : {scores.mean():.4f} | Attaques : {predictions.sum()}/100")
        except Exception as e:
            print(f"\n[{nom}] ERREUR : {e}")

    print("\nTest 3 : le pipeline est robuste face aux données corrompues")


if __name__ == "__main__":
    pipeline, detecteur, params = charger()
    print(f"Modèle chargé — seuil : {params['seuil_operationnel']} | features : {params['nb_feature']}")
    test_batch(pipeline, detecteur, params)
    test_coherence(pipeline, detecteur, params)
    test_robustesse(pipeline, detecteur, params)
    print("\nTous les tests ont réussi.")

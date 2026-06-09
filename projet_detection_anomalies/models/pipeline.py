"""
Pipeline de détection d'anomalies réseau basé sur un Autoencoder.

Étapes :
    1. Preprocesseur    : nettoyage (NaN, inf) + normalisation StandardScaler
    2. AutoencoderDetecteur : calcule le score MSE et prédit 0 (normal) ou 1 (attaque)

Architecture autoencoder : 32 → 8 → 32
"""

import random
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

random.seed(42)
np.random.seed(42)
tf.random.set_seed(42)


class Preprocesseur(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.scaler = StandardScaler()

    def fit(self, X, y=None):
        self.scaler.fit(self._nettoyer(X))
        return self

    def transform(self, X, y=None):
        return self.scaler.transform(self._nettoyer(X))

    @staticmethod
    def _nettoyer(X):
        return X.fillna(0).replace([np.inf, -np.inf], 0)


def construire_autoencoder(nb_features: int) -> keras.Model:
    entree = keras.Input(shape=(nb_features,))
    x = layers.Dense(32, activation="relu")(entree)
    x = layers.Dense(8, activation="relu")(x)
    x = layers.Dense(32, activation="relu")(x)
    sortie = layers.Dense(nb_features, activation="linear")(x)
    modele = keras.Model(entree, sortie)
    modele.compile(optimizer="adam", loss="mse")
    return modele


class AutoencoderDetecteur(BaseEstimator):
    def __init__(self, seuil: float = 0.302, epochs: int = 30, batch_size: int = 256):
        self.seuil = seuil
        self.epochs = epochs
        self.batch_size = batch_size

    def fit(self, X_train, y=None):
        self.model_ = construire_autoencoder(X_train.shape[1])
        self.model_.fit(
            X_train, X_train,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.1,
            verbose=0,
        )
        print(f"Entraîné sur {len(X_train)} flux et {X_train.shape[1]} features")
        return self

    def score_anomalie(self, X) -> np.ndarray:
        reconstruction = self.model_.predict(X, verbose=0)
        return np.mean((X - reconstruction) ** 2, axis=1)

    def predict(self, X) -> np.ndarray:
        return (self.score_anomalie(X) > self.seuil).astype(int)


def construire_pipeline(seuil: float = 0.302):
    pipeline = Pipeline([("preprocessing", Preprocesseur())])
    detecteur = AutoencoderDetecteur(seuil=seuil)
    return pipeline, detecteur


def evaluer(y_test, pred, scores):
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    print(f"  AUC-ROC    : {roc_auc_score(y_test, scores):.4f}")
    print(f"  Précision  : {precision_score(y_test, pred, zero_division=0):.4f}")
    print(f"  Recall     : {recall_score(y_test, pred, zero_division=0):.4f}")
    print(f"  F1-score   : {f1_score(y_test, pred, zero_division=0):.4f}")
    print(f"  Détectées  : {tp} | Fausses alertes : {fp} | Ratées : {fn} | Normaux OK : {tn}")


if __name__ == "__main__":
    from sklearn.model_selection import train_test_split
    from data.ingestion import charger_csv

    chemin = "data/unsw_clean.csv"
    seuil = 0.302

    X, y = charger_csv(chemin)
    X_normal = X[y == 0]
    X_attaque = X[y == 1]

    X_train_raw, X_test_normal_raw = train_test_split(X_normal, test_size=0.2, random_state=42)
    n = len(X_test_normal_raw)
    idx = np.random.choice(len(X_attaque), size=min(n, len(X_attaque)), replace=False)
    X_test_raw = pd.concat([X_test_normal_raw, X_attaque.iloc[idx]])
    y_test = np.array([0] * n + [1] * len(idx))

    pipeline, detecteur = construire_pipeline(seuil=seuil)
    X_train = pipeline.fit_transform(X_train_raw)
    X_test = pipeline.transform(X_test_raw)
    detecteur.fit(X_train)

    scores = detecteur.score_anomalie(X_test)
    predictions = detecteur.predict(X_test)

    print(f"\nSeuil : {seuil}")
    print(f"Score moyen normaux  : {scores[y_test == 0].mean():.4f}")
    print(f"Score moyen attaques : {scores[y_test == 1].mean():.4f}")
    evaluer(y_test, predictions, scores)

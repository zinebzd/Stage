"""
Pipeline de détection d'anomalies réseau basé sur un Autoencoder.

Étapes :
    1. Preprocesseur   : nettoyage (NaN, inf) + normalisation StandardScaler
    2. FeatureEngineer : création de features dérivées (ratio bytes, durée...)
    3. Autoencoder     : architecture 32 -> 8 -> 32, entraîné sur le trafic normal
    4. AutoencoderDetecteur : calcule le score MSE et prédit 0 (normal) ou 1 (attaque)
"""

import random
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
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




class FeatureEngineer(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.col_src = None
        self.col_dst = None
        self.col_dur = None
        self._colonnes_originales = []
        self._actif = False

    def fit(self, X, y=None):
        if isinstance(X, np.ndarray):
            self._actif = False
            return self

        colonnes = [c.lower() for c in X.columns]
        self.col_src = self._trouver(colonnes, ["sbytes", "src_bytes", "totlen_fwd"])
        self.col_dst = self._trouver(colonnes, ["dbytes", "dst_bytes", "totlen_bwd"])
        self.col_dur = self._trouver(colonnes, ["dur", "duration", "flow_duration"])
        self._colonnes_originales = list(X.columns)
        self._actif = True
        return self

    def transform(self, X, y=None):
        if not self._actif or isinstance(X, np.ndarray):
            return X

        X = X.copy()
        cols = self._colonnes_originales

        if self.col_src is not None and self.col_dst is not None:
            X["ratio_bytes"] = X[cols[self.col_src]] / (X[cols[self.col_dst]] + 1e-6)

        if self.col_dur is not None:
            X["log_duration"] = np.log1p(X[cols[self.col_dur]].abs())
            X["short_conn"] = (X[cols[self.col_dur]] < 0.01).astype(int)

        return X

    @staticmethod
    def _trouver(colonnes, candidats):
        for c in candidats:
            if c in colonnes:
                return colonnes.index(c)
        return None


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
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel() #extrait les 4 valeurs de la matrice de confusion
    print(f" AUC-ROC : {roc_auc_score(y_test, scores):.4f}")
    print(f" Précision : {precision_score(y_test, pred, zero_division=0):.4f}")
    print(f" Recall : {recall_score(y_test, pred, zero_division=0):.4f}")
    print(f" f1-score  : {f1_score(y_test, pred, zero_division=0):.4f}")
    print(f" Attaques détectées : {tp}")
    print(f" Fausses alertes: {fp}")
    print(f" Attaques ratées: {fn}")
    print(f" Normaux corrects : {tn}")



if __name__ == "__main__":
    from sklearn.model_selection import train_test_split
    from data.ingestion import charger_csv

    chemin = "../data/unsw_clean.csv"
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

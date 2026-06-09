"""
 Sauvegarder le modèle entraîné avec joblib ou pickle. Sauvegarder aussi le scaler, l'encodeur et les paramètres de features. Documenter le format de sortie.

Jusqu'ici le modèle est entraîné et utilisé dans le même script donc à chaque fois qu'on veut faire une prédiction, il faut tout réentraîner depuis le début.
Le but ici est de séparer l'entraînement de l'utilisation. On entraîne le modèle une seule fois, on sauvegarde tout sur le disque, et ensuite on peut recharger le modèle en quelques secondes pour faire des prédictions sur de nouvelles données sans jamais réentraîner.
On doit sauvegarder 3 choses car le modèle seul ne suffit pas :
    - Le scaler car les nouvelles données doivent être normalisées avec exactement les mêmes paramètres que les données d'entraînement : format .keras
    - Le modèle Keras avec les poids du réseau de neurones appris pendant l'entraînement : format .joblib
    - Les paramètres soient le seuil, les features attendues, la date  pour savoir exactement comment utiliser le modèle : format .json

"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from tensorflow import keras

#imports viennent des nouveaux modules
from models.pipeline import AutoencoderDetecteur, construire_pipeline, evaluer
from data.ingestion import charger_csv

dossier_sauvegarde = "modele_sauvegarde"


def sauvegarder(pipeline, detecteur, noms_features: list, seuil: float):
    os.makedirs(dossier_sauvegarde, exist_ok=True)
    detecteur.model_.save(os.path.join(dossier_sauvegarde, "autoencoder.keras"))
    print(f" autoencoder.keras")
    joblib.dump(pipeline, os.path.join(dossier_sauvegarde, "pipeline_sklearn.joblib"))
    print(f"pipeline_sklearn.joblib")
    parametres = {
        "seuil_operationnel": seuil,
        "nb_feature": len(noms_features),
        "features": noms_features,
        "architecture": "32→8→32",
        "epochs": detecteur.epochs,
        "batch_size": detecteur.batch_size,
        "date_entrainement": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset": "dataset UNSW-NB15",
        "format_sortie": {
            "score_anomalie": "float, erreur MSE — plus c'est élevé, plus c'est suspect",
            "prediction": "int, 0 = normal, 1 = attaque",
            "seuil": "float, si score > seuil alors prediction = 1",
        },
    }
    with open(os.path.join(dossier_sauvegarde, "parametres.json"), "w", encoding="utf-8") as f:
        json.dump(parametres, f, indent=4, ensure_ascii=False)
    print(f" parametres.json")


def charger_modele(dossier: str = dossier_sauvegarde):
    with open(os.path.join(dossier, "parametres.json"), "r", encoding="utf-8") as f:
        parametres = json.load(f)

    pipeline = joblib.load(os.path.join(dossier, "pipeline_sklearn.joblib"))

    detecteur = AutoencoderDetecteur(seuil=parametres["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(os.path.join(dossier, "autoencoder.keras"))

    print(f" Modèle prêt avec un seuil : {parametres['seuil_operationnel']}")
    return pipeline, detecteur, parametres


def predire_depuis_csv(chemin_csv: str, dossier: str = dossier_sauvegarde) -> pd.DataFrame:
    pipeline, detecteur, _ = charger_modele(dossier) 
    df = pd.read_csv(chemin_csv, low_memory=False)
    X = df.select_dtypes(include=[np.number]).fillna(0).replace([np.inf, -np.inf], 0)

    X_normalise = pipeline.transform(X)
    scores = detecteur.score_anomalie(X_normalise)
    predictions = detecteur.predict(X_normalise)

    print(f"[Prédiction] {len(df)} flux | Attaques : {predictions.sum()} ({predictions.mean():.1%})")
    return pd.DataFrame({"score_anomalie": scores, "prediction": predictions})


if __name__ == "__main__":
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


    sauvegarder(pipeline, detecteur, noms_features=list(X.columns), seuil=seuil)


    pipeline2, detecteur2, parametres = charger_modele()
    scores = detecteur2.score_anomalie(X_test)
    predictions = detecteur2.predict(X_test)
    print(f"Date d'entraînement : {parametres['date_entrainement']}")
    evaluer(y_test, predictions, scores)

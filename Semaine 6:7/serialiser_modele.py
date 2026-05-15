"""
 Sauvegarder le modèle entraîné avec joblib ou pickle. Sauvegarder aussi le scaler, l'encodeur et les paramètres de features. Documenter le format de sortie.

Jusqu'ici le modèle est entraîné et utilisé dans le même script donc à chaque fois qu'on veut faire une prédiction, il faut tout réentraîner depuis le début.
Le but ici est de séparer l'entraînement de l'utilisation. On entraîne le modèle une seule fois, on sauvegarde tout sur le disque, et ensuite on peut recharger le modèle en quelques secondes pour faire des prédictions sur de nouvelles données sans jamais réentraîner.
On doit sauvegarder 3 choses car le modèle seul ne suffit pas :
    - Le scaler car les nouvelles données doivent être normalisées avec exactement les mêmes paramètres que les données d'entraînement : format .keras
    - Le modèle Keras avec les poids du réseau de neurones appris pendant l'entraînement : format .joblib
    - Les paramètres soient le seuil, les features attendues, la date  pour savoir exactement comment utiliser le modèle : format .json

"""

# %%
import os
import json
import random
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split

# imports depuis pipeline.py
from pipeline import (ingestion,construire_pipeline,build_autoencoder,AutoencoderDetecteur,evaluer)

import tensorflow as tf
from tensorflow import keras

random.seed(42)
np.random.seed(42)
tf.random.set_seed(42)

# dossier de sauvegarde
dossier = "modele_sauvegarde"
os.makedirs("modele_sauvegarde", exist_ok=True) 


# %%
# Sauvegarde 
# Sauvegarde les 3 éléments du modèle entraîné
#On choisit le format json pour le fichier des paramètres car si tu ouvres le fichier avec n'importe quel éditeur de texte tu vois directement les paramètres contrairement à d'autres formats
# deplus celui-ci est lisible par n'importe quel langage (Python, JavaScript, Java...) et il est léger

def sauvegarder(pipe, detecteur, feature_names: list, seuil: float):
    chemin_keras = os.path.join(dossier, "autoencoder.keras") # Modèle Keras (autoencoder) 
    detecteur.model_.save(chemin_keras)  # sauvegarde poids et architecture
    print(f"Modèle Keras {chemin_keras}")

    chemin_pipe = os.path.join(dossier, "pipeline_sklearn.joblib") # Pipeline sklearn (scaler) 
    joblib.dump(pipe, chemin_pipe)  # sérialise le pipeline sklearn avec joblib car il est plus rapide et plus fiable pour les objets sklearn
    print(f"Pipeline sklearn {chemin_pipe}")

    # Paramètres
    parametres = {
        "seuil_operationnel" : seuil,
        "nb_features"        : len(feature_names),
        "features"           : feature_names,
        "architecture"       : "32→8→32",
        "epochs"             : detecteur.epochs,
        "batch_size"         : detecteur.batch_size,
        "date_entrainement"  : datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset"            : "dataset UNSW-NB15",
        "format_sortie"      : {"score_anomalie" : "float, erreur MSE calculée pour chaque flux réseau plus c'est élevé plus c'est suspect","prediction": "int, 0 pour normal et 1 pour une  attaque","seuil" : "float , si score > seuil alors prediction = 1" }
    }
    # Sauvegarde en format json lisible
    chemin_json = os.path.join(dossier, "parametres.json")
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(parametres, f, indent=4, ensure_ascii=False)
    print(f"Paramètres  {chemin_json}")

# %%
# Chargement
#C' est l'inverse de sauvegarder(). charger_modele relit les 3 fichiers sauvegardés sur le disque et reconstruit le scaler pour normaliser et le détecteur pour prédire. 
# Après avoir appelé cette fonction on peut faire des prédictions immédiatement sans réentraîner

def charger_modele(dossier: str = dossier) -> tuple: #charge les paramètres
    with open(os.path.join(dossier, "parametres.json"), "r", encoding="utf-8") as f:
        parametres = json.load(f)
    pipe = joblib.load(os.path.join(dossier, "pipeline_sklearn.joblib")) # charge le scaler sklearn fitté

    detecteur  = AutoencoderDetecteur(seuil=parametres["seuil_operationnel"]) # recrée le détecteur et charge les poids du réseau de neurones
    detecteur.model_ = keras.models.load_model(os.path.join(dossier, "autoencoder.keras"))

    print(f"Modèle chargé et seuil : {parametres['seuil_operationnel']}")
    return pipe, detecteur, parametres


# %%
# Prédiction
#Le but de cette fonction est qu'on lui donne n'importe quel csv de trafic réseau et elle retourne pour chaque ligne si c'est une attaque ou non. Elle charge automatiquement le modèle sauvegardé

def predire_nouvelles_donnees(chemin_csv: str, dossier: str = dossier) -> pd.DataFrame:
    pipe, detecteur, parametres = charger_modele(dossier) # charge le modèle sauvegardé (scaler, autoencoder et paramètres)
    df = pd.read_csv(chemin_csv, low_memory=False) #charge le nouveau csv et garde uniquement les features numériques
    X  = df.select_dtypes(include=[np.number]).fillna(0).replace([np.inf, -np.inf], 0)
    X_scaled = pipe.transform(X) #  normalise avec le scaler déjà fitté 
    scores = detecteur.score_anomalie(X_scaled)   # calcule le score d'anomalie et la prédiction pour chaque flux
    preds  = detecteur.predict(X_scaled)
    print(f"[Prédiction] {len(df)} flux analysés | Attaques détectées : {preds.sum()} ({preds.mean():.1%})")
    return pd.DataFrame({"score_anomalie": scores, "prediction": preds}) # retourne un DataFrame avec le score et la décision pour chaque flux


# %%
# entraînement, sauvegarde et vérification

if __name__ == "__main__":
    chemin = "../Data/unsw_clean.csv"
    seuil  = 0.302

    print("Entraînement du modèle")
    X, y = ingestion(chemin, label_col='label', normal_val=0)
    X_normal  = X[y == 0]
    X_attaque = X[y == 1]
    X_train_raw, X_test_normal_raw = train_test_split(X_normal, test_size=0.2, random_state=42)

    n  = len(X_test_normal_raw)
    idx  = np.random.choice(len(X_attaque), size=min(n, len(X_attaque)), replace=False)
    X_test_raw = pd.concat([X_test_normal_raw, X_attaque.iloc[idx]])
    y_test = np.array([0] * n + [1] * len(idx))

    pipe, detecteur = construire_pipeline(seuil=seuil)
    X_train = pipe.fit_transform(X_train_raw)
    X_test  = pipe.transform(X_test_raw)
    detecteur.fit(X_train)


    print(" Sauvegarde")
    sauvegarder(pipe, detecteur, feature_names=list(X.columns), seuil=seuil)

    print(" Vérification (rechargement du modèle)")
    pipe2, detecteur2, parametres = charger_modele()
    scores2 = detecteur2.score_anomalie(X_test)
    pred2   = detecteur2.predict(X_test)

    print(f"\nSeuil opérationnel : {parametres['seuil_operationnel']}")
    print(f"Date d'entraînement : {parametres['date_entrainement']}")
    print(f"Features attendues  : {parametres['nb_features']}")
    evaluer(y_test, pred2, scores2)

# %%

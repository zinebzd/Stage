"""
main.py est l'API c'est le fichier qui tourne en permanence et attend des requêtes.
Quand quelqu'un envoie un flux réseau, il le traite et retourne la prédiction.
La documentation Swagger est auto-générée et accessible sur http://localhost:8000/docs

Les 4 endpoints : 
GET / :  utile pour vérifier que l'API tourne.
GET /info : retourne les paramètres du modèle (seuil, features, date d'entraînement). 
POST /predict :  reçoit un flux de 44 features, le passe dans le pipeline (nettoyage + normalisation + autoencoder) et retourne le score et la prédiction.
POST /predict/batch : même chose mais pour plusieurs flux d'un coup. Retourne en plus le nombre total d'attaques et le taux.
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from tensorflow import keras
import sys
import os

# pour importer pipeline.py qui est dans le dossier parent
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "Semaine 6:7"))
from pipeline import AutoencoderDetecteur


#Chargement du modèle

# Chemin vers le dossier contenant les fichiers sauvegardés
# Path(__file__) = chemin de main.py
# .parent.parent = remonte deux dossiers (Semaine 8 → Stage)
# / "Semaine 6:7" / "modele_sauvegarde" = descend dans le bon dossier
dossier = Path(__file__).parent.parent / "Semaine 6:7" / "modele_sauvegarde"

def charger_modele():
    try:
        with open(dossier / "parametres.json", "r", encoding="utf-8") as f: # charge le fichier json contenant seuil, features, architecture...
            params = json.load(f)  
        pipe = joblib.load(dossier / "pipeline_sklearn.joblib") #charge le scaler sklearn fitté sur les données normales
        detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])   # recrée le détecteur avec le seuil opérationnel sauvegardé
        detecteur.model_ = keras.models.load_model(dossier / "autoencoder.keras")      # charge les poids du réseau de neurones
        return pipe, detecteur, params

    except Exception as e:
        raise RuntimeError(f"Impossible de charger le modèle : {e}")    # si un fichier est manquant ou corrompu on arrête l'API

pipe, detecteur, params = charger_modele() # chargement au démarrage que l'on fait une seule fois pour toutes les requêtes



# initialisation FastAPI

app = FastAPI(title = "API Détection d'Anomalies Réseau", description = """ API de détection d'anomalies basée sur un Autoencoder entraîné sur le dataset UNSW-NB15.

## Comment ça marche ?
Le modèle calcule l'**erreur de reconstruction** (MSE) pour chaque flux réseau.
Si un flux normal est bien reconstruit alors l'erreur sera faible alors que pour un flux anormal est mal reconstruit l'erreur sera élevée.
Si l'erreur dépasse le seuil opérationnel, le flux est classé **attaque**.

## Format de sortie
- score_anomalie : un flotant, il s'agit de l'erreur MSE (plus c'est élevé, plus c'est suspect)
- prediction : un entier soit 0 pour normal ou 1 pour une attaque
- is_anomalie : un booléen, true si attaque détectée""",version = "1.0.0",)


# schémas Pydanstic 
#Pydantic valide automatiquement les données donc si quelqu'un envoie un texte au lieu d'un nombre, ou oublie un champ, FastAPI rejette la requête avec une erreur claire .
#Les ... dans Field(...) signifient que le champ est obligatoire donc si il manque, la requête est rejetée.

# Ce qu'on reçoit en entrée pour /predict
class FluxReseau(BaseModel):
    features: List[float] = Field(..., description="44 features numériques du flux")    # liste de 44 nombres flottants, les features du flux réseau


# Ce qu'on reçoit en entrée pour /predict/batch
class BatchFlux(BaseModel):
    flux: List[FluxReseau] = Field(..., description="Liste de flux à analyser")     # liste de plusieurs FluxReseau


# Ce qu'on retourne pour /predict
class ResultatPrediction(BaseModel):
    score_anomalie : float  # erreur MSE du flux
    prediction : int    # 0 pour normal et 1 pour attaque
    is_anomalie : bool   # true si attaque
    seuil_utilise  : float  # seuil utilisé pour la décision (0.302)

# Ce qu'on retourne pour /predict/batch
class ResultatBatch(BaseModel):
    nb_flux  : int                      # nombre total de flux analysés
    nb_attaques   : int                      # nombre d'attaques détectées
    taux_attaques : float                    # pourcentage d'attaques
    predictions : List[ResultatPrediction] # résultats détaillés par flux

# Ce qu'on retourne pour /info
class InfoModele(BaseModel):
    architecture : str    # "32→8→32"
    nb_feature : int    # 44
    seuil_operationnel : float  # 0.302
    date_entrainement  : str    # "2026-05-12 10:34"
    dataset : str    # " dataset UNSW-NB15"
    format_sortie   : dict   # documentation du format de sortie


#Endpoints

# Endpoint 1 : GET /
@app.get("/", tags=["Général"])  # @app.get dit à FastAPI cette fonction répond aux requêtes GET sur "/"
def health_check():
    # retourne juste un dict pour confirmer que l'API tourne
    return {"status" : "ok","message" : "API de détection d'anomalies réseau opérationnelle",
        "modele"  : params["architecture"],  # ex : "32→8→32"
        "dataset" : params["dataset"]   # ex : " dataset UNSW-NB15"
    }


# Endpoint 2 : GET /info 
@app.get("/info", response_model=InfoModele, tags=["Général"])  # response_model valide que la réponse correspond au schéma InfoModele
def info_modele():
    return InfoModele(**params)  # décompresse le dict params dans les champs de InfoModele


# Endpoint 3 : POST /predict
@app.post("/predict", response_model=ResultatPrediction, tags=["Prédiction"])
def predict(flux: FluxReseau):  # FastAPI valide automatiquement que flux contient bien une liste de floats
    n_features = params["nb_feature"]
    if len(flux.features) != n_features: # vérifie que le nombre de features est exactement 44
        raise HTTPException(
            status_code=422,  # 422 = données invalides
            detail=f"Nombre de features incorrect : {len(flux.features)} reçues, {n_features} attendues" )
    X = pd.DataFrame([flux.features], columns=params["features"])     # conversion en DataFrame avec les noms de colonnes attendus par le scaler
    X_scaled = pipe.transform(X)     # nettoyage et normalisation avec le scaler fitté

    # calcul du score et de la prédiction
    score = float(detecteur.score_anomalie(X_scaled)[0])  # [0] car on a un seul flux
    pred  = int(detecteur.predict(X_scaled)[0])

    return ResultatPrediction(score_anomalie = round(score, 6),prediction = pred,is_anomalie = bool(pred == 1),seuil_utilise  = params["seuil_operationnel"])


# Endpoint 4 : POST /predict/batch 
@app.post("/predict/batch", response_model=ResultatBatch, tags=["Prédiction"])
def predict_batch(batch: BatchFlux):
    n_features = params["nb_feature"]
    if len(batch.flux) == 0:     # vérifie que le batch n'est pas vide
        raise HTTPException(status_code=422, detail="Le batch est vide")
    for i, flux in enumerate(batch.flux):     # vérifie que chaque flux a exactement 44 features
        if len(flux.features) != n_features:
            raise HTTPException(
                status_code=422,
                detail=f"Flux {i} : {len(flux.features)} features reçues, {n_features} attendues")

    # construit un DataFrame avec tous les flux du batch
    X = pd.DataFrame([flux.features for flux in batch.flux], columns=params["features"])

    # preprocessing et prédiction sur tous les flux d'un coup
    X_scaled = pipe.transform(X)
    scores = detecteur.score_anomalie(X_scaled)
    preds  = detecteur.predict(X_scaled)

    # construit la liste des résultats détaillés avec un par flux
    predictions = [ResultatPrediction(score_anomalie = round(float(s), 6),prediction = int(p),is_anomalie = bool(p == 1),seuil_utilise  = params["seuil_operationnel"])
        for s, p in zip(scores, preds)  # zip associe chaque score à sa prédiction
    ]

    return ResultatBatch(
        nb_flux = len(preds),
        nb_attaques   = int(preds.sum()),                      # nombre total d'attaques
        taux_attaques = round(float(preds.mean()) * 100, 2),  # pourcentage d'attaques
        predictions  = predictions )


#test
if __name__ == "__main__":
    print("Modèle chargé avec succès")
    print(f"Seuil : {params['seuil_operationnel']}")
    print(f"Features : {params['nb_feature']}")
    print(f"Dataset : {params['dataset']}")
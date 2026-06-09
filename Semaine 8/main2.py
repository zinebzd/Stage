"""
Jusqu'ici l'API détecte les attaques mais ne les mémorise nulle part — quand tu relances le serveur tout est perdu.
Maintenant on veut stocker les résultats et pouvoir les consulter et filtrer.

Ajout de l'endpoint GET /anomalies avec :
    - filtres : date, sévérité, IP source, type d'attaque
    - pagination : page + limite
    - stockage : SQLite via database.py

Les endpoints existants (/predict, /predict/batch) sauvegardent maintenant automatiquement les anomalies détectées dans la base de données.
"""

import json
import joblib
import numpy as np
import pandas as pd
from math import ceil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from tensorflow import keras
import sys

sys.path.append(str(Path(__file__).parent.parent / "Semaine 6:7"))
from pipeline import AutoencoderDetecteur
from database import sauvegarder_anomalie, get_anomalies, creer_table

#Chargement du modèle
dossier = Path(__file__).parent.parent / "Semaine 6:7" / "modele_sauvegarde"

def charger_modele():
    with open(dossier / "parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)
    pipe = joblib.load(dossier / "pipeline_sklearn.joblib")
    detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(dossier / "autoencoder.keras")
    return pipe, detecteur, params

pipe, detecteur, params = charger_modele()
creer_table()  # crée la table SQLite si elle n'existe pas

# Initialisation Fastapi
app = FastAPI(title = "API Détection d'Anomalies Réseau",description = "API de détection d'anomalies basée sur un Autoencoder entraîné sur le dataset UNSW-NB15.",version = "2.0.0",)

# Schémas Pydantic

class FluxReseau(BaseModel):
    features : List[float] = Field(..., description="44 features numériques du flux")
    ip_source : Optional[str] = Field(None, description="Adresse IP source (optionnel)")
    type_attaque : Optional[str] = Field(None, description="Nom de l'attaque suspectée (optionnel)")
   
class BatchFlux(BaseModel):
    flux: List[FluxReseau] = Field(..., description="Liste de flux à analyser")

class ResultatPrediction(BaseModel):
    score_anomalie : float
    prediction     : int
    is_anomalie    : bool
    severite       : str    # low, medium, high selon le score
    seuil_utilise  : float

class ResultatBatch(BaseModel):
    nb_flux       : int
    nb_attaques   : int
    taux_attaques : float
    predictions   : List[ResultatPrediction]

class InfoModele(BaseModel):
    architecture       : str
    nb_feature         : int
    seuil_operationnel : float
    date_entrainement  : str
    dataset            : str
    format_sortie      : dict

class Anomalie(BaseModel): #C'est le modèle d'une seule anomalie telle qu'elle est stockée en base de données
    id             : int
    date           : str
    ip_source      : Optional[str]
    type_attaque   : Optional[str]
    severite       : str
    score_anomalie : float
    prediction     : int

class ReponseAnomalies(BaseModel): #C'est le modèle de la réponse complète de GET /anomalies
    total        : int    # nombre total de résultats
    page         : int    # page courante
    nb_pages     : int    # nombre total de pages
    limite       : int    # résultats par page
    anomalies    : List[Anomalie]


# Fonction utilitaire qui traduit le score MSE en niveau de danger lisible pour quelqu'un 
def calculer_severite(score: float) -> str:
    if score < 1.0:
        return "low"
    elif score < 10.0:
        return "medium"
    else:
        return "high"


# Endpoints

@app.get("/", tags=["Général"])
def health_check():
    return {"status": "ok", "modele": params["architecture"], "dataset": params["dataset"]}


@app.get("/info", response_model=InfoModele, tags=["Général"])
def info_modele():
    return InfoModele(**params)


@app.post("/predict", response_model=ResultatPrediction, tags=["Prédiction"])
def predict(flux: FluxReseau):
    n_features = params["nb_feature"]
    if len(flux.features) != n_features:  # vérifie qu'on a exactement 44 features
        raise HTTPException(status_code=422, detail=f"{len(flux.features)} features reçues, {n_features} attendues")
    X = pd.DataFrame([flux.features], columns=params["features"])  # convertit en DataFrame
    X_scaled = pipe.transform(X)                                           # normalisation
    score = float(detecteur.score_anomalie(X_scaled)[0])               # calcul du score MSE
    pred = int(detecteur.predict(X_scaled)[0])                        # 0 pour normal et 1 pour attaque
    severite = calculer_severite(score)  # traduit le score en low/medium/high
    if pred == 1:  # on ne sauvegarde que les attaques pas les flux normaux
        sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, score, pred)
    return ResultatPrediction(score_anomalie = round(score, 6),prediction = pred,is_anomalie = bool(pred == 1),severite = severite,seuil_utilise  = params["seuil_operationnel"])


@app.post("/predict/batch", response_model=ResultatBatch, tags=["Prédiction"])
def predict_batch(batch: BatchFlux):
    n_features = params["nb_feature"]
    if len(batch.flux) == 0:
        raise HTTPException(status_code=422, detail="Le batch est vide")
    for i, flux in enumerate(batch.flux):
        if len(flux.features) != n_features:
            raise HTTPException(status_code=422, detail=f"Flux {i} : {len(flux.features)} features reçues")
    X = pd.DataFrame([f.features for f in batch.flux], columns=params["features"])
    X_scaled = pipe.transform(X)
    scores   = detecteur.score_anomalie(X_scaled)
    preds    = detecteur.predict(X_scaled)
    predictions = []
    for i, (s, p, flux) in enumerate(zip(scores, preds, batch.flux)):     # boucle pour calculer la sévérité et sauvegarder si c'est une attaque    
        severite = calculer_severite(float(s)) #calcul de la sévérité pour ce flux
        if p == 1:
            sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, float(s), int(p))
        predictions.append(ResultatPrediction(score_anomalie = round(float(s), 6),prediction = int(p),is_anomalie= bool(p == 1),severite= severite,seuil_utilise  = params["seuil_operationnel"]))

    return ResultatBatch(
        nb_flux = len(preds),
        nb_attaques   = int(preds.sum()),
        taux_attaques = round(float(preds.mean()) * 100, 2),
        predictions = predictions)


# permet de consulter et filtrer les attaques depuis la base SQLite.
@app.get("/anomalies", response_model=ReponseAnomalies, tags=["Historique"])
def get_anomalies_endpoint(
    # Optional[str] = Query(None) signifie que le paramètre est facultatif donc si l'utilisateur ne le fournit pas, il vaut None et le filtre est ignoré
    date : Optional[str] = Query(None, description="Filtre par date"),
    severite : Optional[str] = Query(None, description="Filtre par sévérité : low, medium, high"),
    ip : Optional[str] = Query(None, description="Filtre par adresse IP source"),
    type_attaque : Optional[str] = Query(None, description="Filtre par type d'attaque"),
    # Paramètres pagination
    page : int = Query(1,  description="Numéro de page", ge=1), #ge=1 signifie >= 1
    limite : int   = Query(20, description="Résultats par page", ge=1, le=100)):
    if severite and severite not in ["low", "medium", "high"]:     # Validation manuelle de la sévérité
        raise HTTPException(status_code=422, detail="severite doit être : low, medium ou high")
    anomalies, total = get_anomalies(date, severite, ip, type_attaque, page, limite)
    nb_pages = ceil(total / limite) if total > 0 else 1 #nb de pages 47 anomalies / 20 par page = 2.35 donc 3 pages (si total == 0 on retourne 1 page plutôt que 0 pour éviter nb_pages=0)
    return ReponseAnomalies(total = total,page= page,nb_pages = nb_pages,limite = limite, anomalies = anomalies)

if __name__ == "__main__":
    print(f"Modèle chargé avec un seuil : {params['seuil_operationnel']} et features : {params['nb_feature']}")

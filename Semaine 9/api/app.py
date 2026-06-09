"""
API de détection d'anomalies réseau — version 4.

Endpoints disponibles :
    GET  /  : santé de l'API
    GET  /info :informations sur le modèle chargé
    POST /predict : analyse un seul flux réseau (JSON)
    POST /predict/batch : analyse un batch de flux (JSON)
    GET  /anomalies : historique paginé des anomalies détectées
    POST /analyze  : analyse un fichier CSV ou JSON uploadé
    GET  /stats : statistiques globales sur les anomalies en base

uvicorn api.app:app --reload --port 8000
Documentation : http://localhost:8000/docs
"""

import io
import csv
import json
import joblib
import numpy as np
import pandas as pd
from math import ceil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from tensorflow import keras

# imports sont réorganisés
from models.pipeline import AutoencoderDetecteur
from api.database import sauvegarder_anomalie, get_anomalies, creer_table, get_connection
from utils.helpers import calculer_severite #calculer_severite vient maintenant de utils/helpers.py



DOSSIER_MODELE = Path(__file__).parent.parent.parent / "Semaine 6:7" / "modele_sauvegarde"


def charger_modele():
    """Charge le pipeline sklearn, l'autoencoder et les paramètres depuis le disque."""
    with open(DOSSIER_MODELE / "parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)
    pipeline = joblib.load(DOSSIER_MODELE / "pipeline_sklearn.joblib")
    detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(DOSSIER_MODELE / "autoencoder.keras")
    return pipeline, detecteur, params


pipeline, detecteur, params = charger_modele()
creer_table()




app = FastAPI(title="API Détection d'Anomalies Réseau",description="Détection d'anomalies basée sur un Autoencoder entraîné sur UNSW-NB15.",version="4.0.0",)



class FluxReseau(BaseModel):
    features: List[float] = Field(..., description="Features numériques du flux")
    ip_source: Optional[str] = Field(None, description="Adresse IP source (optionnel)")
    type_attaque: Optional[str] = Field(None, description="Type d'attaque suspecté (optionnel)")

class BatchFlux(BaseModel):
    flux: List[FluxReseau] = Field(..., description="Liste de flux à analyser")

class ResultatPrediction(BaseModel):
    score_anomalie: float
    prediction: int
    is_anomalie: bool
    severite: str
    seuil_utilise: float

class ResultatBatch(BaseModel):
    nb_flux: int
    nb_attaques: int
    taux_attaques: float
    predictions: List[ResultatPrediction]

class InfoModele(BaseModel):
    architecture: str
    nb_feature: int
    seuil_operationnel: float
    date_entrainement: str
    dataset: str
    format_sortie: dict

class Anomalie(BaseModel):
    id: int
    date: str
    ip_source: Optional[str]
    type_attaque: Optional[str]
    severite: str
    score_anomalie: float
    prediction: int

class ReponseAnomalies(BaseModel):
    total: int
    page: int
    nb_pages: int
    limite: int
    anomalies: List[Anomalie]

class ResultatAnalyse(BaseModel):
    ligne: int
    score_anomalie: float
    prediction: int
    is_anomalie: bool
    severite: str
    seuil_utilise: float

class ReponseAnalyse(BaseModel):
    nb_flux_analyses: int
    nb_anomalies: int
    taux_anomalies: float
    resultats: List[ResultatAnalyse]

class Stats(BaseModel):
    total_anomalies: int
    total_low: int
    total_medium: int
    total_high: int
    score_moyen: float
    score_max: float
    score_min: float
    top_ips: List[dict]
    top_types: List[dict]
    anomalies_par_jour: List[dict]




@app.get("/", tags=["général"])
def health_check():
    return {"status": "ok", "modele": params["architecture"], "dataset": params["dataset"]}


@app.get("/info", response_model=InfoModele, tags=["général"])
def info_modele():
    return InfoModele(**params)



@app.post("/predict", response_model=ResultatPrediction, tags=["prédiction"])
def predict(flux: FluxReseau):
    nb_features = params["nb_feature"]
    if len(flux.features) != nb_features:
        raise HTTPException(status_code=422, detail=f"{len(flux.features)} features reçues, {nb_features} attendues")

    X = pd.DataFrame([flux.features], columns=params["features"])
    X_normalise = pipeline.transform(X)
    score = float(detecteur.score_anomalie(X_normalise)[0])
    prediction = int(detecteur.predict(X_normalise)[0])
    severite = calculer_severite(score)

    if prediction == 1:
        sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, score, prediction)

    return ResultatPrediction(
        score_anomalie=round(score, 6),
        prediction=prediction,
        is_anomalie=prediction == 1,
        severite=severite,
        seuil_utilise=params["seuil_operationnel"],
    )


@app.post("/predict/batch", response_model=ResultatBatch, tags=["prédiction"])
def predict_batch(batch: BatchFlux):
    nb_features = params["nb_feature"]

    if not batch.flux:
        raise HTTPException(status_code=422, detail="Le batch est vide")

    for i, flux in enumerate(batch.flux):
        if len(flux.features) != nb_features:
            raise HTTPException(status_code=422, detail=f"Flux {i} : {len(flux.features)} features reçues, {nb_features} attendues")

    X = pd.DataFrame([f.features for f in batch.flux], columns=params["features"])
    X_normalise = pipeline.transform(X)
    scores = detecteur.score_anomalie(X_normalise)
    predictions = detecteur.predict(X_normalise)

    resultats = []
    for score_val, pred_val, flux in zip(scores, predictions, batch.flux):
        score = float(score_val)
        pred = int(pred_val)
        severite = calculer_severite(score)
        if pred == 1:
            sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, score, pred)
        resultats.append(ResultatPrediction(
            score_anomalie=round(score, 6),
            prediction=pred,
            is_anomalie=pred == 1,
            severite=severite,
            seuil_utilise=params["seuil_operationnel"],
        ))

    return ResultatBatch(
        nb_flux=len(predictions),
        nb_attaques=int(predictions.sum()),
        taux_attaques=round(float(predictions.mean()) * 100, 2),
        predictions=resultats,
    )




@app.get("/anomalies", response_model=ReponseAnomalies, tags=["historique"])
def get_anomalies_endpoint(
    date: Optional[str] = Query(None, description="Filtre par date (ex. '2026-05')"),
    severite: Optional[str] = Query(None, description="Filtre par sévérité : low, medium, high"),
    ip: Optional[str] = Query(None, description="Filtre par IP source"),
    type_attaque: Optional[str] = Query(None, description="Filtre par type d'attaque"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limite: int = Query(20, ge=1, le=100, description="Résultats par page"),
):
    if severite and severite not in ("low", "medium", "high"):
        raise HTTPException(status_code=422, detail="severite doit être : low, medium ou high")

    anomalies, total = get_anomalies(date, severite, ip, type_attaque, page, limite)
    nb_pages = ceil(total / limite) if total > 0 else 1

    return ReponseAnomalies(
        total=total,
        page=page,
        nb_pages=nb_pages,
        limite=limite,
        anomalies=anomalies,
    )


@app.post("/analyze", response_model=ReponseAnalyse, tags=["analyse fichier"])
async def analyze_fichier(fichier: UploadFile = File(...)):
    nom = fichier.filename or ""
    if not nom.endswith(".csv") and not nom.endswith(".json"):
        raise HTTPException(status_code=422, detail=f"Format non supporté : '{nom}'. Seuls .csv et .json sont acceptés.")

    contenu = await fichier.read()
    if not contenu.strip():
        raise HTTPException(status_code=422, detail="Le fichier est vide")

    try:
        donnees = _lire_csv(contenu) if nom.endswith(".csv") else _lire_json(contenu)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Impossible de lire le fichier : {e}")

    if not donnees:
        raise HTTPException(status_code=422, detail="Le fichier ne contient aucune donnée")
    if len(donnees) > 10_000:
        raise HTTPException(status_code=422, detail=f"Fichier trop grand : {len(donnees)} lignes, maximum autorisé : 10 000")

    nb_features = params["nb_feature"]
    for i, ligne in enumerate(donnees):
        if len(ligne) != nb_features:
            raise HTTPException(status_code=422, detail=f"Ligne {i+1} : {len(ligne)} features reçues, {nb_features} attendues")

    X = pd.DataFrame(donnees, columns=params["features"])
    X_normalise = pipeline.transform(X)
    scores = detecteur.score_anomalie(X_normalise)
    predictions = detecteur.predict(X_normalise)

    resultats = []
    for i, (score_val, pred_val) in enumerate(zip(scores, predictions)):
        score = float(score_val)
        pred = int(pred_val)
        severite = calculer_severite(score)
        if pred == 1:
            sauvegarder_anomalie(None, None, severite, score, pred)
        resultats.append(ResultatAnalyse(
            ligne=i + 1,
            score_anomalie=round(score, 6),
            prediction=pred,
            is_anomalie=pred == 1,
            severite=severite,
            seuil_utilise=params["seuil_operationnel"],
        ))

    return ReponseAnalyse(
        nb_flux_analyses=len(predictions),
        nb_anomalies=int(predictions.sum()),
        taux_anomalies=round(float(predictions.mean()) * 100, 2),
        resultats=resultats,
    )



@app.get("/stats", response_model=Stats, tags=["statistiques"])
def get_stats():
    conn = get_connection()

    stats_globales = conn.execute("""
        SELECT COUNT(*) AS total, AVG(score_anomalie) AS score_moyen,
               MAX(score_anomalie) AS score_max, MIN(score_anomalie) AS score_min
        FROM anomalies
    """).fetchone()

    total = stats_globales["total"] or 0
    if total == 0:
        conn.close()
        return Stats(total_anomalies=0, total_low=0, total_medium=0, total_high=0,
                     score_moyen=0.0, score_max=0.0, score_min=0.0,
                     top_ips=[], top_types=[], anomalies_par_jour=[])

    total_low    = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'low'").fetchone()[0]
    total_medium = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'medium'").fetchone()[0]
    total_high   = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'high'").fetchone()[0]

    top_ips = [
        {"ip": row["ip_source"], "nb_attaques": row["nb_attaques"]}
        for row in conn.execute("""
            SELECT ip_source, COUNT(*) AS nb_attaques FROM anomalies
            WHERE ip_source IS NOT NULL
            GROUP BY ip_source ORDER BY nb_attaques DESC LIMIT 5
        """).fetchall()
    ]

    top_types = [
        {"type": row["type_attaque"], "nb_occurrences": row["nb_occurrences"]}
        for row in conn.execute("""
            SELECT type_attaque, COUNT(*) AS nb_occurrences FROM anomalies
            WHERE type_attaque IS NOT NULL
            GROUP BY type_attaque ORDER BY nb_occurrences DESC LIMIT 5
        """).fetchall()
    ]

    anomalies_par_jour = [
        {"jour": row["jour"], "nb_anomalies": row["nb_anomalies"]}
        for row in conn.execute("""
            SELECT substr(date, 1, 10) AS jour, COUNT(*) AS nb_anomalies
            FROM anomalies WHERE date >= date('now', '-7 days')
            GROUP BY jour ORDER BY jour ASC
        """).fetchall()
    ]

    conn.close()
    return Stats(
        total_anomalies=total,
        total_low=total_low, total_medium=total_medium, total_high=total_high,
        score_moyen=round(float(stats_globales["score_moyen"]), 6),
        score_max=round(float(stats_globales["score_max"]), 6),
        score_min=round(float(stats_globales["score_min"]), 6),
        top_ips=top_ips, top_types=top_types, anomalies_par_jour=anomalies_par_jour,
    )




def _lire_csv(contenu: bytes) -> list:
 
    try:
        texte = contenu.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Encodage invalide")

    reader = csv.reader(io.StringIO(texte))
    premiere_ligne = next(reader, None)
    if premiere_ligne is None:
        return []

    try:
        # si la première ligne contient des nombres → c'est une ligne de données
        premiere_ligne_float = [float(v) for v in premiere_ligne if v.strip()]
        lignes = [premiere_ligne_float] + [
            [float(v) for v in ligne if v.strip()]
            for ligne in reader if any(v.strip() for v in ligne)
        ]
    except ValueError:
        # la première ligne contient du texte → c'est un en-tête, on l'ignore
        lignes = []
        for i, ligne in enumerate(reader):
            valeurs = [v for v in ligne if v.strip()]
            if not valeurs:
                continue
            try:
                lignes.append([float(v) for v in valeurs])
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Ligne {i+2} contient des valeurs non numériques")

    return lignes


def _lire_json(contenu: bytes) -> list:
    try:
        texte = contenu.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Encodage invalide")

    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"JSON invalide : {e}")

    if not isinstance(donnees, list):
        raise HTTPException(status_code=422, detail="Le fichier json doit être une liste de listes")

    resultat = []
    for i, element in enumerate(donnees):
        if not isinstance(element, list):
            raise HTTPException(status_code=422, detail=f"Élément {i+1} doit être une liste de nombres")
        try:
            resultat.append([float(v) for v in element])
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail=f"Élément {i+1} contient des valeurs non numériques")

    return resultat

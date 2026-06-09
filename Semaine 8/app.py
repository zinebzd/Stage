"""

on regroupe tous les endpoints des versions précédentes et ajoute GET /stats.
GET  /stats  inxlut les statistiques globales sur toutes les anomalies détectées 
"""

import io
import csv
import json
import sqlite3
import joblib
import numpy as np
import pandas as pd
from math import ceil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from tensorflow import keras
import sys

sys.path.append(str(Path(__file__).parent.parent / "Semaine 6:7"))
from pipeline import AutoencoderDetecteur
from database import sauvegarder_anomalie, get_anomalies, creer_table, get_connection


# chargement du modèle au démarrage
dossier = Path(__file__).parent.parent / "Semaine 6:7" / "modele_sauvegarde"

def charger_modele():
    with open(dossier / "parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)
    pipe = joblib.load(dossier / "pipeline_sklearn.joblib")
    detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(dossier / "autoencoder.keras")
    return pipe, detecteur, params

pipe, detecteur, params = charger_modele()
creer_table()


# initialisation fastapi

app = FastAPI(title="API Détection dAnomalies Réseau",description="API de détection danomalies réseau basée sur un Autoencoder entraîné sur le dataset UNSW-NB15.",version="4.0.0",)


# schémas pydantic pour les entrées et sorties de lapi

class FluxReseau(BaseModel):
    features     : List[float]   = Field(..., description="44 features numériques du flux")
    ip_source    : Optional[str] = Field(None, description="adresse ip source (optionnel)")
    type_attaque : Optional[str] = Field(None, description="type dattaque suspecté (optionnel)")

class BatchFlux(BaseModel):
    flux: List[FluxReseau] = Field(..., description="liste de flux à analyser")

class ResultatPrediction(BaseModel):
    score_anomalie : float
    prediction     : int
    is_anomalie    : bool
    severite       : str
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

class Anomalie(BaseModel):
    id             : int
    date           : str
    ip_source      : Optional[str]  
    type_attaque   : Optional[str]  
    severite       : str
    score_anomalie : float
    prediction     : int

class ReponseAnomalies(BaseModel):
    total     : int            
    page      : int           
    nb_pages  : int           
    limite    : int            
    anomalies : List[Anomalie] 

class ResultatAnalyse(BaseModel):
    ligne          : int   
    score_anomalie : float 
    prediction     : int    
    is_anomalie    : bool  
    severite       : str    
    seuil_utilise  : float  

class ReponseAnalyse(BaseModel):
    nb_flux_analyses : int                 
    nb_anomalies     : int                   
    taux_anomalies   : float                
    resultats        : List[ResultatAnalyse]


 # ce quon retourne pour GET /stats
class Stats(BaseModel):
    total_anomalies    : int            # nombre total d'anomalies en base
    total_low          : int            # nombre d'anomalies de sévérité low
    total_medium       : int            # nombre d'anomalies de sévérité medium
    total_high         : int            # nombre d'anomalies de sévérité high
    score_moyen        : float          # score mse moyen de toutes les anomalies
    score_max          : float          # score mse le plus élevé jamais détecté
    score_min          : float          # score mse le plus faible détecté
    top_ips            : List[dict]     # top 5 des adresses ip les plus suspectes
    top_types          : List[dict]     # top 5 des types dattaques les plus fréquents
    anomalies_par_jour : List[dict]     # nombre danomalies par jour sur les 7 derniers jours


# fonction utilitaire
def calculer_severite(score: float) -> str:
    # traduit lerreur mse en niveau de danger lisible
    if score < 1.0:
        return "low"
    elif score < 10.0:
        return "medium"
    else:
        return "high"


# endpoints existants

@app.get("/", tags=["général"])
def health_check():
    return {"status": "ok", "modele": params["architecture"], "dataset": params["dataset"]}


@app.get("/info", response_model=InfoModele, tags=["général"])
def info_modele():
    return InfoModele(**params)



@app.post("/predict", response_model=ResultatPrediction, tags=["prédiction"])
def predict(flux: FluxReseau):
    n_features = params["nb_feature"]
    if len(flux.features) != n_features:
        raise HTTPException(status_code=422, detail=f"{len(flux.features)} features reçues, {n_features} attendues")
    X = pd.DataFrame([flux.features], columns=params["features"])
    X_scaled = pipe.transform(X)
    score  = float(detecteur.score_anomalie(X_scaled)[0])
    pred  = int(detecteur.predict(X_scaled)[0])
    severite = calculer_severite(score)
    if pred == 1:
        sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, score, pred)
    return ResultatPrediction(score_anomalie = round(score, 6),prediction= pred,is_anomalie = bool(pred == 1),severite = severite,seuil_utilise  = params["seuil_operationnel"])



@app.post("/predict/batch", response_model=ResultatBatch, tags=["prédiction"])
def predict_batch(batch: BatchFlux):
    n_features = params["nb_feature"]
    if len(batch.flux) == 0:
        raise HTTPException(status_code=422, detail="le batch est vide")
    for i, flux in enumerate(batch.flux):
        if len(flux.features) != n_features:
            raise HTTPException(status_code=422, detail=f"flux {i} : {len(flux.features)} features reçues")
    X = pd.DataFrame([f.features for f in batch.flux], columns=params["features"])
    X_scaled = pipe.transform(X)
    scores = detecteur.score_anomalie(X_scaled)
    preds  = detecteur.predict(X_scaled)
    predictions = []
    for i, (s, p, flux) in enumerate(zip(scores, preds, batch.flux)):
        severite = calculer_severite(float(s))
        if p == 1:
            sauvegarder_anomalie(flux.ip_source, flux.type_attaque, severite, float(s), int(p))
        predictions.append(ResultatPrediction(
            score_anomalie = round(float(s), 6),
            prediction     = int(p),
            is_anomalie    = bool(p == 1),
            severite       = severite,
            seuil_utilise  = params["seuil_operationnel"]
        ))
    return ResultatBatch(nb_flux = len(preds),nb_attaques  = int(preds.sum()),taux_attaques = round(float(preds.mean()) * 100, 2),predictions= predictions)



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


@app.post("/analyze", response_model=ReponseAnalyse, tags=["analyse fichier"])
async def analyze_fichier(fichier: UploadFile = File(...)):
    nom = fichier.filename
    if not nom.endswith(".csv") and not nom.endswith(".json"):     # accepte uniquement csv et json 
        raise HTTPException(
            status_code=422,
            detail=f"format non supporté : {nom} , seul les fichier csv ou json sont acceptés")
    contenu = await fichier.read() #lit le contenu brut du fichier uploadé et le met dans la variable contenu sous forme de bytes, await permet d'attendre que la lecture soit terminée avant de passer à la ligne suivante
    if not contenu.strip():     # on vérifie que le fichier n'est pas vide avant de le décoder
        raise HTTPException(status_code=422, detail="le fichier est vide")
    try:
        if nom.endswith(".csv"):
            donnees = _lire_csv(contenu)
        else:
            donnees = _lire_json(contenu)

    except HTTPException: # on laisse remonter les erreurs http quon a déjà bien formatées
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"impossible de lire le fichier : {str(e)}")
    if len(donnees) == 0:     # validation du nombre de lignes 
        raise HTTPException(status_code=422, detail="le fichier ne contient aucune donnée")

    if len(donnees) > 10000:
        raise HTTPException(
            status_code=422,
            detail=f"fichier trop grand : {len(donnees)} lignes détectées, maximum autorisé 10000")

    n_features = params["nb_feature"] # validation du nombre de features par ligne 
    for i, ligne in enumerate(donnees):
        if len(ligne) != n_features:
            raise HTTPException(
                status_code=422,
                detail=f"ligne {i+1} : {len(ligne)} features reçues, {n_features} attendues")

    #  pipeline de détection , même pipeline que /predict et /predict/batch
    X  = pd.DataFrame(donnees, columns=params["features"])
    X_scaled = pipe.transform(X)
    scores = detecteur.score_anomalie(X_scaled)
    preds = detecteur.predict(X_scaled)

    resultats = []  # construction des résultats et sauvegarde des attaques 
    for i, (s, p) in enumerate(zip(scores, preds)):
        severite = calculer_severite(float(s))
        if p == 1: # sauvegarde en base si cest une attaque
            sauvegarder_anomalie(None, None, severite, float(s), int(p))         # ip et type dattaque sont None car un fichier de logs brut ne les contient pas
        resultats.append(ResultatAnalyse(ligne = i + 1,score_anomalie = round(float(s), 6),prediction = int(p),is_anomalie = bool(p == 1),severite = severite,seuil_utilise  = params["seuil_operationnel"]))
    nb_anomalies = int(preds.sum())
    return ReponseAnalyse(nb_flux_analyses = len(preds),nb_anomalies = nb_anomalies,taux_anomalies = round(float(preds.mean()) * 100, 2),resultats= resultats)


# endpoint statistiques
# retourne des statistiques globales sur toutes les anomalies détectées en base
@app.get("/stats", response_model=Stats, tags=["statistiques"])
def get_stats():
    conn = get_connection()
    # compte le total et calcule les scores min max et moyen en une seule requête
    stats_globales = conn.execute("""
        SELECT
            COUNT(*)            AS total,
            AVG(score_anomalie) AS score_moyen,
            MAX(score_anomalie) AS score_max,
            MIN(score_anomalie) AS score_min
        FROM anomalies
    """).fetchone()
    total = stats_globales["total"] or 0     # si la base est vide on retourne des zéros plutôt quune erreur
    if total == 0:
        conn.close()
        return Stats(total_anomalies= 0,total_low = 0,total_medium  = 0,total_high  = 0,score_moyen= 0.0,score_max  = 0.0,score_min = 0.0,top_ips  = [],top_types = [],anomalies_par_jour = [])
    # une requête par sévérité pour avoir le détail low medium high
    total_low    = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'low'").fetchone()[0]
    total_medium = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'medium'").fetchone()[0]
    total_high   = conn.execute("SELECT COUNT(*) FROM anomalies WHERE severite = 'high'").fetchone()[0]

    # top 5 des ips les plus suspectes 
    # groupe par ip source et compte combien dattaques viennent de chaque ip et exclut les None 
    top_ips_rows = conn.execute("""
        SELECT ip_source, COUNT(*) AS nb_attaques
        FROM anomalies
        WHERE ip_source IS NOT NULL
        GROUP BY ip_source
        ORDER BY nb_attaques DESC
        LIMIT 5
    """).fetchall()
    top_ips = [{"ip": row["ip_source"], "nb_attaques": row["nb_attaques"]} for row in top_ips_rows]     # convertit en liste de dicts lisibles

    # top 5 des types dattaques les plus fréquents 
    top_types_rows = conn.execute("""
        SELECT type_attaque, COUNT(*) AS nb_occurrences
        FROM anomalies
        WHERE type_attaque IS NOT NULL
        GROUP BY type_attaque
        ORDER BY nb_occurrences DESC
        LIMIT 5
    """).fetchall()
    top_types = [{"type": row["type_attaque"], "nb_occurrences": row["nb_occurrences"]} for row in top_types_rows]

    # anomalies par jour sur les 7 derniers jours 
    anomalies_jour_rows = conn.execute("""
        SELECT substr(date, 1, 10) AS jour, COUNT(*) AS nb_anomalies 
        FROM anomalies
        WHERE date >= date('now', '-7 days')
        GROUP BY jour
        ORDER BY jour ASC
    """).fetchall()     # substr extrait les 10 premiers caractères de la date
    anomalies_par_jour = [{"jour": row["jour"], "nb_anomalies": row["nb_anomalies"]} for row in anomalies_jour_rows]

    conn.close()

    return Stats(total_anomalies = total,total_low = total_low,total_medium = total_medium,total_high  = total_high,
        score_moyen = round(float(stats_globales["score_moyen"]), 6),score_max  = round(float(stats_globales["score_max"]), 6),score_min = round(float(stats_globales["score_min"]), 6),
        top_ips = top_ips,top_types  = top_types,anomalies_par_jour = anomalies_par_jour )

# fonctions appelées uniquement par /analyze

# lit un fichier csv et retourne une liste de listes de floats et gère automatiquement la présence ou l'absence d'en-tête
def _lire_csv(contenu: bytes) -> list:
    try:
        texte = contenu.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="encodage invalide")
    reader = csv.reader(io.StringIO(texte))
    premiere_ligne = next(reader, None) #  lit la première ligne pour détecter si c'est un en-tête ou des données
    if premiere_ligne is None:
        return []
    try:
        premiere_ligne_float = [float(v) for v in premiere_ligne if v.strip()]         # si la première ligne contient des nombres c'est une ligne de données
        lignes = [premiere_ligne_float] + [
            [float(v) for v in ligne if v.strip()]
            for ligne in reader
            if any(v.strip() for v in ligne)]  # ignore les lignes complètement vides
    
    except ValueError:
        lignes = []        # la première ligne contient du texte c'est un en-tête donc on l'ignore
        for i, ligne in enumerate(reader):
            ligne_propre = [v for v in ligne if v.strip()]
            if not ligne_propre:
                continue  # ignore les lignes vides
            try:
                lignes.append([float(v) for v in ligne_propre])
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"ligne {i+2} contient des valeurs non numériques" )
    return lignes

# lit un fichier json et retourne une liste de listes de floats    
def _lire_json(contenu: bytes) -> list:
    try:
        texte = contenu.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="encodage invalide")
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"json invalide : {str(e)}")
    if not isinstance(donnees, list):     # vérifie que c'est une liste
        raise HTTPException(
            status_code=422,
            detail="Le fichier json doit être une liste de listes")
    resultat = []     # vérifie que chaque élément est une liste de nombres
    for i, element in enumerate(donnees):
        if not isinstance(element, list):
            raise HTTPException(
                status_code=422,
                detail=f"élément {i+1}  doit être une liste de nombres, reçu {type(element).__name__}")
        try:
            resultat.append([float(v) for v in element])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail=f"élément {i+1} contient des valeurs non numériques")
    return resultat

if __name__ == "__main__":
    print(f"modèle chargé — seuil : {params['seuil_operationnel']} | features : {params['nb_feature']}")

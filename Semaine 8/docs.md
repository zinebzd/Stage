# Documentation API : détection d'Anomalies Réseau

## Vue d'ensemble

API REST construite avec FastAPI pour détecter les intrusions réseau en temps réel.
Le modèle est un Autoencoder (32→8→32) entraîné sur le dataset UNSW-NB15.

La documentation interactive est auto-générée par FastAPI et accessible sur :
- Swagger UI  : http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Installation et lancement

```bash
pip install fastapi uvicorn tensorflow scikit-learn joblib pandas numpy pytest httpx
uvicorn main:app --reload
pytest tests/ -v
```

---

## Principe de détection

Le modèle a été entraîné uniquement sur du trafic normal.
Il sait bien reconstruire les flux normaux ainsi l'erreur MSE est faible.
Il reconstruit mal les attaques donc l'erreur MSE est élevée donc détection.
Un flux réseau est d'abord nettoyé et normalisé, puis passé dans l'autoencoder qui calcule son erreur de reconstruction (score MSE). Ce score est ensuite comparé au seuil opérationnel de 0.302 pour prendre la décision finale : normal ou attaque.
---

## Endpoints

### GET /
Vérifie que l'API est en ligne.

```json
{"status": "ok", "modele": "32→8→32", "dataset": "UNSW-NB15"}
```

---

### GET /info
Retourne les paramètres du modèle chargé.

```json
{
  "architecture"       : "32→8→32",
  "nb_feature"         : 44,
  "seuil_operationnel" : 0.302,
  "date_entrainement"  : "2026-05-12 10:34",
  "dataset"            : "dataset UNSW-NB15"
}
```

---

### POST /predict
Analyse un seul flux réseau. Le vecteur doit contenir exactement 44 valeurs numériques.

Requête :
```json
{"features": [0.1, 0.5, 1.2, 0.0, ...]}
```

Réponse :
```json
{"score_anomalie": 0.0412, "prediction": 0, "is_anomalie": false, "seuil_utilise": 0.302}
```

---

### POST /predict/batch
Analyse plusieurs flux en une seule requête.

Requête :
```json
{"flux": [{"features": [0.1, ...]}, {"features": [10.0, ...]}]}
```

Réponse :
```json
{
  "nb_flux": 2, "nb_attaques": 1, "taux_attaques": 50.0,
  "predictions": [
    {"score_anomalie": 0.04, "prediction": 0, "is_anomalie": false, "seuil_utilise": 0.302},
    {"score_anomalie": 12.3, "prediction": 1, "is_anomalie": true,  "seuil_utilise": 0.302}
  ]
}
```

---

## Format de sortie
Le modèle retourne quatre informations pour chaque flux analysé. Le score_anomalie est un nombre décimal représentant l'erreur MSE donc plus il est élevé, plus le flux est suspect. La prediction est un entier valant 0 pour un flux normal ou 1 pour une attaque détectée. is_anomalie est un booléen qui vaut True si le score dépasse le seuil. Enfin seuil_utilise indique le seuil opérationnel retenu, fixé à 0.302.
Erreur 422 signifie nombre de features incorrect ou batch vide.
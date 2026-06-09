# AnomalyNet — Plateforme de détection d'anomalies réseau

## Prérequis

- Python **3.11** (obligatoire pour TensorFlow)
- Node.js **18+**
- macOS ou Linux

---

## Installation — Backend (API Python)

```bash
# 1. Aller dans le dossier projet
cd projet_detection_anomalies

# 2. Créer l'environnement virtuel Python 3.11
python3.11 -m venv .venv

# 3. Activer le venv
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
```

---

## Installation — Frontend (React)

```bash
cd frontend
npm install
```

---

## Lancer la plateforme

### Terminal 1 — API FastAPI

```bash
cd projet_detection_anomalies
source .venv/bin/activate
uvicorn api.app:app --reload --port 8000
```

L'API est disponible sur : http://localhost:8000
Documentation Swagger : http://localhost:8000/docs

### Terminal 2 — Dashboard React

```bash
cd projet_detection_anomalies/frontend
npm run dev
```

Le dashboard est disponible sur : http://localhost:5173

---

## Connexion au dashboard

Trois comptes de démonstration :

| Rôle           | Identifiant  | Mot de passe |
|----------------|-------------|--------------|
| Admin          | admin       | admin123     |
| Top Management | direction   | top123       |
| Analyste       | analyste    | user123      |

---

## Fonctionnalités par rôle

| Page              | Admin | Top Management | Analyste |
|-------------------|:-----:|:--------------:|:--------:|
| Dashboard         |  ✓   |       ✓        |    —     |
| Statistiques      |  ✓   |       ✓        |    —     |
| Historique        |  ✓   |       ✓        |    ✓     |
| Prédiction        |  ✓   |       —        |    ✓     |
| Batch             |  ✓   |       —        |    ✓     |
| Analyser fichier  |  ✓   |       —        |    ✓     |
| Administration    |  ✓   |       —        |    —     |

---

## Tester avec un fichier réel

Un fichier de test est disponible à la racine :

```
test_reel.csv   — 500 lignes du dataset UNSW-NB15 (44 features numériques)
```

Aller sur la page **Analyser**, uploader ce fichier et lancer l'analyse.

---

## Structure du projet

```
projet_detection_anomalies/
├── api/
│   ├── app.py          — API FastAPI (9 endpoints)
│   └── database.py     — Base de données SQLite
├── models/
│   └── pipeline.py     — Autoencoder de détection
├── utils/
│   └── helpers.py      — Fonctions partagées
├── data/
│   └── ingestion.py    — Chargement des données
├── tests/              — 42 tests automatiques
├── modele_sauvegarde/  — Modèle entraîné (UNSW-NB15)
├── frontend/           — Dashboard React
├── anomalies.db        — Base de données (générée automatiquement)
└── requirements.txt
```

---

## Lancer les tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

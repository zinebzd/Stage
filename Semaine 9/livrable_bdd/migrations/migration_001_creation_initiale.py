"""
Ici le but de ce fichier est de créer les 4 tables dans la base de données la première fois.
Elle ne s'exécute qu'une seule fois grâce à la table 'migrations' qui garde en mémoire quelles migrations ont déjà été appliquées.

Tables créées :
- anomalies : résultats de détection du modèle
- logs  : données brutes importées des CSV
- statistiques : résumés calculés périodiquement
- alertes : alertes critiques déclenchées automatiquement
"""

import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from schema import schema_anomalie, schema_log, schema_stat, schema_alerte, index

num_mig = "001"
description = "Création initiale des tables anomalies, logs, statistiques, alertes"

#crée toutes les tables et les index
def appliquer(conn: sqlite3.Connection) -> None:
    conn.executescript(schema_anomalie) # exécutent le SQL défini dans schema.py
    conn.executescript(schema_log)
    conn.executescript(schema_stat)
    conn.executescript(schema_alerte)
    conn.executescript(index)
    print(f" Toutes les tables et index ont été créés")
    print(f" Migration {num_mig} appliquée avec succès.")

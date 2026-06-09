"""
Le but de ce fichier a d'ajouter de la colonne log_type dans la table logs.
Elle ajoute une colonne qui n'existait pas dans la migration 001.

"""

import sqlite3

num_mig = "002"
description = "Ajout colonne log_type dans la table logs"


def appliquer(conn: sqlite3.Connection) -> None:
    colonnes = [row[1] for row in conn.execute("PRAGMA table_info(logs)").fetchall()]     # vérifie d'abord si la colonne existe déjà pour éviter une erreur

    if "log_type" not in colonnes:
        conn.execute("ALTER TABLE logs ADD COLUMN log_type TEXT DEFAULT NULL")
        print(" Colonne log_type ajoutée.")
    else:
        print(" Colonne log_type déjà présente.")

    print(f" Migration {num_mig} appliquée avec succès.")

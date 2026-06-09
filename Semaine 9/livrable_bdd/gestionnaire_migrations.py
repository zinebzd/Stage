"""
Ce fichier a un seul rôle celui-ci étant d'exécuter les migrations dans le bon ordre, sans jamais en appliquer une deux fois.

Il effectue ces action dans cet ordre :
- Crée une table 'migrations' qui garde en mémoire ce qui a déjà été fait
- Lit tous les fichiers migration_XXX_*.py dans le dossier migrations/
- Applique uniquement les migrations pas encore exécutées
-  Enregistre chaque migration appliquée avec la date d'exécution

"""

import sqlite3
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

db_path = Path(__file__).parent / "detection_anomalies.db"
dossier_migrations = Path(__file__).parent / "migrations"
dossier_modele= Path("/Users/home/Desktop/Stage/Semaine 6:7/modele_sauvegarde")

# Ouvre une connexion à la base de données
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")     # active les clés étrangères (désactivées par défaut dans SQLite)
    return conn


# Crée la table qui garde en mémoire les migrations déjà appliquées
def creer_table_migrations(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT    NOT NULL UNIQUE,   -- ex. '001', '002'
            description TEXT    NOT NULL,          -- description lisible
            date_appliquee TEXT NOT NULL           -- date d'exécution
        )
    """)
    conn.commit()


# Retourne l'ensemble des numéros de migrations déjà appliquées
def migrations_appliquees(conn: sqlite3.Connection) -> set:
    rows = conn.execute("SELECT numero FROM migrations").fetchall()
    return {row["numero"] for row in rows}

#Charge dynamiquement un fichier de migration Python
def charger_migration(chemin: Path):
    spec = importlib.util.spec_from_file_location(chemin.stem, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Exécute toutes les migrations non encore appliquées dans l'ordre
def executer_migrations() -> None:
    print(f"Base de données : {db_path}")
    conn = get_connection()
    creer_table_migrations(conn) # vérifier que la table migrations existe
    deja_appliquees = migrations_appliquees(conn)
    print(f"Migrations déjà appliquées : {deja_appliquees or 'aucune'}")
    fichiers = sorted(dossier_migrations.glob("migration_*.py")) #lister tous les fichiers de migration triés par numéro
    if not fichiers:
        print("Aucun fichier de migration trouvé.")
        return
    nb_appliquees = 0 #appliquer les migrations manquantes
    for fichier in fichiers:
        module = charger_migration(fichier)
        numero = module.num_mig
        description = module.description

        if numero in deja_appliquees: # migration est déjà dans la table migrations
            print(f"Ignoré")
            continue

        print(f"\n Migration {numero} — {description}")
        try:
            module.appliquer(conn) 
            conn.execute( # enregistre la migration comme appliquée
                "INSERT INTO migrations (numero, description, date_appliquee) VALUES (?, ?, ?)",(numero, description, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            nb_appliquees += 1
            print(f"Migration {numero} enregistrée.")
        except Exception as e:
            conn.rollback()
            print(f" Migration {numero} échouée : {e}")
            sys.exit(1)

    conn.close()

    if nb_appliquees == 0:
        print("\nAucune nouvelle migration à appliquer.")
    else:
        print(f"\n{nb_appliquees} migration(s) appliquée(s) avec succès.")


if __name__ == "__main__":
    executer_migrations()

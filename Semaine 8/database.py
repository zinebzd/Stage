"""
On crée une base de données SQLite (un simple fichier anomalies.db sur ton disque) avec une table qui stocke 
pour chaque anomalie : la date, l'IP source, le type d'attaque, la sévérité, le score et la prédiction.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "anomalies.db"

#fonction qui ouvre une connexion à la base de données SQLite
def get_connection():
    conn = sqlite3.connect(DB_PATH)     # ouvre le fichier anomalies.db et retourne une connexion si le fichier n'existe pas encore, SQLite le crée automatiquement
    conn.row_factory = sqlite3.Row     # par défaut SQLite retourne les lignes comme des tuples avec Row on peut accéder aux colonnes par leur nom
    return conn

#fonction qui crée la table SQLite au démarrage de l'API
def creer_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,         
            ip_source       TEXT,                    
            type_attaque    TEXT,                    
            severite        TEXT    NOT NULL,       
            score_anomalie  REAL    NOT NULL,       
            prediction      INTEGER NOT NULL   
        )     
    """ )
    conn.commit()
    conn.close()

# sauvegarde une anomalie détectée dans la base de données
def sauvegarder_anomalie(ip_source, type_attaque, severite, score_anomalie, prediction):
    conn = get_connection()
    conn.execute("""
        INSERT INTO anomalies (date, ip_source, type_attaque, severite, score_anomalie, prediction)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip_source, type_attaque, severite, score_anomalie, prediction))
    conn.commit()
    conn.close()

# récupère les anomalies avec filtres optionnels et pagination
def get_anomalies(date=None, severite=None, ip=None, type_attaque=None, page=1, limite=20):
    conn = get_connection()
    # construction dynamique de la requête selon les filtres fournis
    conditions = []
    valeurs    = []
    if date:
        conditions.append("date LIKE ?")
        valeurs.append(f"{date}%")          # filtre sur le début de la date

    if severite: #filtre sévérité
        conditions.append("severite = ?")
        valeurs.append(severite)

    if ip: #filtre IP source
        conditions.append("ip_source = ?")
        valeurs.append(ip)

    if type_attaque: #filtre type d'attaque
        conditions.append("type_attaque = ?")
        valeurs.append(type_attaque)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # compte total pour la pagination
    total = conn.execute(f"SELECT COUNT(*) FROM anomalies {where}", valeurs).fetchone()[0]

    # calcul de l'offset pour la pagination
    offset = (page - 1) * limite
    valeurs_page = valeurs + [limite, offset]

    rows = conn.execute(f"SELECT * FROM anomalies {where} ORDER BY date DESC LIMIT ? OFFSET ?",valeurs_page).fetchall()
    conn.close()
    return [dict(row) for row in rows], total


# création de la table au démarrage
creer_table()

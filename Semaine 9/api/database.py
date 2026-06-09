"""
Couche d'accès à la base de données SQLite.
La base anomalies.db est créée automatiquement au premier démarrage de l'API.
Elle stocke chaque anomalie détectée pour l'historique et les statistiques.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "anomalies.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def creer_table() -> None:
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            date           TEXT    NOT NULL,
            ip_source      TEXT,
            type_attaque   TEXT,
            severite       TEXT    NOT NULL,
            score_anomalie REAL    NOT NULL,
            prediction     INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def sauvegarder_anomalie(ip_source: Optional[str],type_attaque: Optional[str],severite: str,score_anomalie: float,prediction: int,) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO anomalies (date, ip_source, type_attaque, severite, score_anomalie, prediction)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip_source, type_attaque, severite, score_anomalie, prediction),
    )
    conn.commit()
    conn.close()


def get_anomalies(date: Optional[str] = None,severite: Optional[str] = None,ip: Optional[str] = None,type_attaque: Optional[str] = None,page: int = 1,limite: int = 20,) -> tuple:
    conn = get_connection()
    conditions = []
    valeurs = []
    if date:
        conditions.append("date LIKE ?")
        valeurs.append(f"{date}%")
    if severite:
        conditions.append("severite = ?")
        valeurs.append(severite)
    if ip:
        conditions.append("ip_source = ?")
        valeurs.append(ip)
    if type_attaque:
        conditions.append("type_attaque = ?")
        valeurs.append(type_attaque)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM anomalies {where}", valeurs).fetchone()[0]

    offset = (page - 1) * limite
    rows = conn.execute(
        f"SELECT * FROM anomalies {where} ORDER BY date DESC LIMIT ? OFFSET ?",
        valeurs + [limite, offset],
    ).fetchall()

    conn.close()
    return [dict(row) for row in rows], total

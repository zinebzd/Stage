"""
Couche d'accès à la base de données SQLite.

La base anomalies.db est créée automatiquement au premier démarrage de l'API.
Elle stocke chaque anomalie détectée pour l'historique et les statistiques.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "anomalies.db"


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
    # table qui trace tous les flux analysés (normaux + attaques) pour le ratio
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flux_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT    NOT NULL,
            nb_flux      INTEGER NOT NULL,
            nb_anomalies INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def enregistrer_flux(nb_flux: int, nb_anomalies: int) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO flux_log (date, nb_flux, nb_anomalies) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nb_flux, nb_anomalies),
    )
    conn.commit()
    conn.close()


def get_kpis() -> dict:
    conn = get_connection()

    # total flux analysés (table flux_log)
    row_flux = conn.execute("SELECT COALESCE(SUM(nb_flux), 0) AS total FROM flux_log").fetchone()
    total_flux = row_flux["total"]

    # anomalies
    row_ano = conn.execute("""
        SELECT COUNT(*) AS total,
               COALESCE(AVG(score_anomalie), 0) AS score_moyen,
               COALESCE(MAX(date), NULL) AS derniere_date
        FROM anomalies
    """).fetchone()
    total_anomalies = row_ano["total"]
    score_moyen     = round(float(row_ano["score_moyen"]), 4)
    derniere_date   = row_ano["derniere_date"]

    # dernière analyse (flux_log ou anomalies, la plus récente)
    row_last = conn.execute("""
        SELECT MAX(date) AS d FROM flux_log
    """).fetchone()
    derniere_analyse = row_last["d"] or derniere_date or "—"

    # taux d'anomalies
    taux = round((total_anomalies / total_flux * 100), 2) if total_flux > 0 else 0.0

    # sévérité dominante
    row_sev = conn.execute("""
        SELECT severite, COUNT(*) AS n FROM anomalies
        GROUP BY severite ORDER BY n DESC LIMIT 1
    """).fetchone()
    severite_dominante = row_sev["severite"] if row_sev else "—"

    conn.close()
    return {
        "total_flux_analyses": total_flux,
        "total_anomalies":     total_anomalies,
        "taux_anomalies":      taux,
        "score_moyen":         score_moyen,
        "derniere_analyse":    derniere_analyse,
        "severite_dominante":  severite_dominante,
    }


def get_timeline(granularite: str = "jour") -> list:
    conn = get_connection()
    if granularite == "heure":
        tronquer = "substr(date, 1, 13)"   # YYYY-MM-DD HH
        label    = "substr(date, 1, 13) || ':00'"
    else:
        tronquer = "substr(date, 1, 10)"   # YYYY-MM-DD
        label    = "substr(date, 1, 10)"

    # anomalies par période depuis la table anomalies
    anomalies = conn.execute(f"""
        SELECT {label} AS periode,
               COUNT(*) AS nb_anomalies,
               SUM(CASE WHEN severite='high'   THEN 1 ELSE 0 END) AS nb_high,
               SUM(CASE WHEN severite='medium' THEN 1 ELSE 0 END) AS nb_medium,
               SUM(CASE WHEN severite='low'    THEN 1 ELSE 0 END) AS nb_low
        FROM anomalies
        GROUP BY {tronquer}
        ORDER BY {tronquer} ASC
    """).fetchall()

    # total flux par période depuis flux_log
    flux = conn.execute(f"""
        SELECT {label} AS periode, SUM(nb_flux) AS nb_flux_total
        FROM flux_log
        GROUP BY {tronquer}
        ORDER BY {tronquer} ASC
    """).fetchall()
    conn.close()

    flux_map = {r["periode"]: r["nb_flux_total"] for r in flux}
    return [
        {
            "periode":      r["periode"],
            "nb_anomalies": r["nb_anomalies"],
            "nb_high":      r["nb_high"],
            "nb_medium":    r["nb_medium"],
            "nb_low":       r["nb_low"],
            "nb_flux_total": flux_map.get(r["periode"], r["nb_anomalies"]),
        }
        for r in anomalies
    ]


def sauvegarder_anomalie(
    ip_source: Optional[str],
    type_attaque: Optional[str],
    severite: str,
    score_anomalie: float,
    prediction: int,
) -> None:
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


def get_anomalies(
    date: Optional[str] = None,
    severite: Optional[str] = None,
    ip: Optional[str] = None,
    type_attaque: Optional[str] = None,
    page: int = 1,
    limite: int = 20,
) -> tuple:
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

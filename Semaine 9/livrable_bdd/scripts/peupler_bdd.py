"""
Le but de ce fichier est de remplir les 4 tables avec des vraies données.
C'est lui qui fait le lien entre tes fichiers CSV et la base de données.
Ce script lit les 3 fichiers CSV, passe chaque ligne dans le pipeline
de détection, et insère les résultats dans les tables logs, anomalies,
statistiques et alertes.

Les fichiers traités sont :
- unsw_clean.csv : dataset principal d'entraînement (700 001 lignes)
- cicids_clean.csv : dataset secondaire (223 080 lignes)
- logs_clean.csv  : logs réseau réels simulés (colonnes différentes)

"""

import json
import sqlite3
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from tensorflow import keras

# Chemins
base_dir     = Path(__file__).parent.parent
db_path      = base_dir / "detection_anomalies.db"
modele_dir   = Path("/Users/home/Desktop/Stage/Semaine 6:7/modele_sauvegarde")
data_dir     = Path("/Users/home/Desktop/Stage/Data")
unsw_path    = data_dir / "unsw_clean.csv"
cicids_path  = data_dir / "cicids_clean.csv"
logs_path    = data_dir / "logs_clean.csv"



# Chargement du modèle
#Charge le pipeline sklearn et l'autoencoder depuis modele_sauvegarde/."""
def charger_modele():
    import sys
    sys.path.insert(0, "/Users/home/Desktop/Stage/Semaine 9")
    sys.path.insert(0, "/Users/home/Desktop/Stage/Semaine 6:7")  # ← ajoute cette ligne
    from models.pipeline import AutoencoderDetecteur
    from tensorflow import keras

    with open(modele_dir / "parametres.json", "r", encoding="utf-8") as f:
        params = json.load(f)

    pipeline = joblib.load(modele_dir / "pipeline_sklearn.joblib")
    detecteur = AutoencoderDetecteur(seuil=params["seuil_operationnel"])
    detecteur.model_ = keras.models.load_model(modele_dir / "autoencoder.keras")

    return pipeline, detecteur, params


# Calcul de la sévérité
def calculer_severite(score: float) -> str:
    if score < 1.0:
        return "low"
    elif score < 10.0:
        return "medium"
    else:
        return "high"



# Insertion dans logs et anomalies
#Insère un batch de résultats dans logs et anomalies
def inserer_batch(conn: sqlite3.Connection,lignes: list[dict],) -> tuple[int, int]:
    nb_anomalies = 0
    for ligne in lignes:
        # Insertion dans logs (tous les flux)
        cursor = conn.execute("""
            INSERT INTO logs (
                analyse, ip_source, ip_destination, protocole,
                port_destination, score_anomalie, prediction, severite,
                dataset_source, type_attaque, action, log_type, bytes_transferes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ligne.get("analyse"),
            ligne.get("ip_source"),
            ligne.get("ip_destination"),
            ligne.get("protocole"),
            ligne.get("port_destination"),
            ligne["score_anomalie"],
            ligne["prediction"],
            ligne.get("severite"),
            ligne["dataset_source"],
            ligne.get("type_attaque"),
            ligne.get("action"),
            ligne.get("log_type"),
            ligne.get("bytes_transferes"),
        ))

        log_id = cursor.lastrowid
        if ligne["prediction"] == 1:         # insertion dans anomalies (uniquement les attaques)
            conn.execute("""
                INSERT INTO anomalies (
                    log_id, date_detection, ip_source, ip_destination,
                    protocole, type_attaque, severite, score_anomalie, dataset_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                ligne.get("analyse"),
                ligne.get("ip_source"),
                ligne.get("ip_destination"),
                ligne.get("protocole"),
                ligne.get("type_attaque"),
                ligne["severite"],
                ligne["score_anomalie"],
                ligne["dataset_source"],
            ))
            nb_anomalies += 1

    return len(lignes), nb_anomalies



# Traitement de unsw_clean.csv
#lit unsw_clean.csv et passe dans le pipeline et insère dans la BDD

def traiter_unsw(conn: sqlite3.Connection, pipeline, detecteur, params, limite: int = None):
    df = pd.read_csv(unsw_path, low_memory=False)
    if limite:
        df = df.head(limite)
    print(f"UNSW a {len(df)} lignes chargées.")
    features = params["features"]     # Colonnes numériques attendues par le modèle
    colonnes_numeriques = df.select_dtypes(include=[np.number]).columns.tolist()

    # on garde uniquement les features connues du modèle
    features_disponibles = [f for f in features if f in colonnes_numeriques]
    X = df[features_disponibles].fillna(0).replace([np.inf, -np.inf], 0)

    for feature in features:     # compléter avec des zéros si des features manquent
        if feature not in X.columns:
            X[feature] = 0.0
    X = X[features]

    X_normalise  = pipeline.transform(X)
    scores       = detecteur.score_anomalie(X_normalise)
    predictions  = detecteur.predict(X_normalise)

    batch_size = 1000     # préparation des lignes à insérer
    total_logs = total_anomalies = 0

    for debut in range(0, len(df), batch_size):
        fin = min(debut + batch_size, len(df))
        batch = df.iloc[debut:fin]

        lignes = []
        for i, (_, row) in enumerate(batch.iterrows()):
            idx    = debut + i
            score  = float(scores[idx])
            pred   = int(predictions[idx])
            sev    = calculer_severite(score) if pred == 1 else None

            # récupère le type d'attaque depuis la colonne attack_cat si disponible
            type_attaque = None
            if "attack_cat" in row and pd.notna(row["attack_cat"]):
                type_attaque = str(row["attack_cat"]).strip()
                if type_attaque in ("Normal", ""):
                    type_attaque = None

            #génère une date fictive pour simuler un historique sur 30 jours
            jours_offset  = (idx % 30)
            analyse  = (datetime(2026, 4, 1) + timedelta(days=jours_offset)).strftime("%Y-%m-%d %H:%M:%S")

            lignes.append({
                "analyse"    : analyse,
                "ip_source"       : str(row.get("srcip", "")) or None,
                "ip_destination"  : str(row.get("dstip", "")) or None,
                "protocole"       : str(row.get("proto", "")) or None,
                "port_destination": int(row["dsport"]) if pd.notna(row.get("dsport")) and str(row.get("dsport", "")).isdigit() else None,
                "score_anomalie"  : round(score, 6),
                "prediction"      : pred,
                "severite"        : sev,
                "dataset_source"  : "unsw",
                "type_attaque"    : type_attaque,
                "action"          : None,
                "log_type"        : None,
                "bytes_transferes": int(row["sbytes"]) if pd.notna(row.get("sbytes")) else None,
            })

        nb_l, nb_a = inserer_batch(conn, lignes)
        total_logs      += nb_l
        total_anomalies += nb_a

        if debut % 10000 == 0:
            conn.commit()
            print(f"Dataset UNSW possède {fin}/{len(df)} lignes traitées et {total_anomalies} attaques détectées")
    conn.commit()
    print(f" Dataset UNSW possède {total_logs} logs et {total_anomalies} anomalies")
    return total_logs, total_anomalies



# Traitement de cicids_clean.csv
#  lit cicids_clean.csv et passe dans le pipeline et insère dans la BDD

def traiter_cicids(conn: sqlite3.Connection, pipeline, detecteur, params, limite: int = None):
    df = pd.read_csv(cicids_path, low_memory=False)
    if limite:
        df = df.head(limite)
    features = params["features"]
    colonnes_numeriques = df.select_dtypes(include=[np.number]).columns.tolist()
    features_disponibles = [f for f in features if f in colonnes_numeriques]
    X = df[features_disponibles].fillna(0).replace([np.inf, -np.inf], 0)

    for feature in features:
        if feature not in X.columns:
            X[feature] = 0.0
    X = X[features]

    X_normalise  = pipeline.transform(X)
    scores       = detecteur.score_anomalie(X_normalise)
    predictions  = detecteur.predict(X_normalise)

    batch_size = 1000
    total_logs = total_anomalies = 0

    for debut in range(0, len(df), batch_size):
        fin   = min(debut + batch_size, len(df))
        batch = df.iloc[debut:fin]

        lignes = []
        for i, (_, row) in enumerate(batch.iterrows()):
            idx  = debut + i
            score = float(scores[idx])
            pred  = int(predictions[idx])
            sev   = calculer_severite(score) if pred == 1 else None

            # Label original du dataset cicids
            type_attaque = str(row.get("Label", "")).strip()
            if type_attaque in ("BENIGN", ""):
                type_attaque = None

            jours_offset = (idx % 30)
            analyse = (datetime(2026, 4, 1) + timedelta(days=jours_offset)).strftime("%Y-%m-%d %H:%M:%S")

            lignes.append({
                "analyse"    : analyse,
                "ip_source"       : None,   # cicids ne contient pas les IPs
                "ip_destination"  : None,
                "protocole"       : None,
                "port_destination": int(row["Destination Port"]) if pd.notna(row.get("Destination Port")) else None,
                "score_anomalie"  : round(score, 6),
                "prediction"      : pred,
                "severite"        : sev,
                "dataset_source"  : "cicids",
                "type_attaque"    : type_attaque,
                "action"          : None,
                "log_type"        : None,
                "bytes_transferes": None,
            })

        nb_l, nb_a = inserer_batch(conn, lignes)
        total_logs      += nb_l
        total_anomalies += nb_a

        if debut % 10000 == 0:
            conn.commit()
            print(f"Dataset CICIDS possède {fin}/{len(df)} lignes traitées et {total_anomalies} attaques détectées")

    conn.commit()
    print(f"Dataset CICIDS possède{total_logs} logs et {total_anomalies} anomalies")
    return total_logs, total_anomalies



# Traitement de logs_clean.csv
#  lit logs_clean.csv et insère directement dans la BDD.
# Ce fichier contient déjà des informations réseau structurées  sans nécessiter de passer dans le pipeline ML. 
# On calcule un score fictif basé sur le champ threat_label

def traiter_logs_clean(conn: sqlite3.Connection, limite: int = None):
    df = pd.read_csv(logs_path, low_memory=False)
    if limite:
        df = df.head(limite)
    batch_size = 1000
    total_logs = total_anomalies = 0
    for debut in range(0, len(df), batch_size):
        fin   = min(debut + batch_size, len(df))
        batch = df.iloc[debut:fin]

        lignes = []
        for _, row in batch.iterrows():
            threat = str(row.get("threat_label", "benign")).lower().strip()

            # On déduit prediction et score depuis le label existant
            est_attaque = threat not in ("benign", "normal", "")
            pred        = 1 if est_attaque else 0

            # Score fictif cohérent avec la sévérité
            if not est_attaque:
                score = round(np.random.uniform(0.01, 0.3), 6)
            elif threat in ("suspicious",):
                score = round(np.random.uniform(1.0, 5.0), 6)
            else:
                score = round(np.random.uniform(5.0, 25.0), 6)

            sev = calculer_severite(score) if pred == 1 else None

            # timestamp depuis la colonne timestamp du fichier
            analyse = str(row.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            lignes.append({
                "analyse"    : analyse,
                "ip_source"       : str(row.get("source_ip", "")) or None,
                "ip_destination"  : str(row.get("dest_ip", "")) or None,
                "protocole"       : str(row.get("protocol", "")) or None,
                "port_destination": None,
                "score_anomalie"  : score,
                "prediction"      : pred,
                "severite"        : sev,
                "dataset_source"  : "logs_clean",
                "type_attaque"    : threat if est_attaque else None,
                "action"          : str(row.get("action", "")) or None,
                "log_type"        : str(row.get("log_type", "")) or None,
                "bytes_transferes": int(row["bytes_transferred"]) if pd.notna(row.get("bytes_transferred")) else None,
            })

        nb_l, nb_a = inserer_batch(conn, lignes)
        total_logs      += nb_l
        total_anomalies += nb_a

        if debut % 10000 == 0:
            conn.commit()
            print(f"Dataset Logs possède {fin}/{len(df)} lignes traitées et {total_anomalies} attaques")

    conn.commit()
    print(f"Dataset Logs a {total_logs} logs et {total_anomalies} anomalies")
    return total_logs, total_anomalies



# Calcul des statistiques

#  calcule et insère un snapshot de statistiques par jour dans la table statistiques
def calculer_statistiques(conn: sqlite3.Connection) -> None:
    # récupère les jours distincts présents dans anomalies
    jours = conn.execute("""
        SELECT DISTINCT substr(date_detection, 1, 10) AS jour
        FROM anomalies
        ORDER BY jour
    """).fetchall()

    for (jour,) in jours:
        # Total logs ce jour
        total_logs = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE analyse LIKE ?", (f"{jour}%",)
        ).fetchone()[0]

        # Statistiques anomalies ce jour
        stats = conn.execute("""
            SELECT
                COUNT(*)            AS total,
                AVG(score_anomalie) AS score_moyen,
                MAX(score_anomalie) AS score_max,
                MIN(score_anomalie) AS score_min,
                SUM(severite = 'low')    AS nb_low,
                SUM(severite = 'medium') AS nb_medium,
                SUM(severite = 'high')   AS nb_high
            FROM anomalies
            WHERE date_detection LIKE ?
        """, (f"{jour}%",)).fetchone()

        total_anomalies = stats[0] or 0
        taux = round(total_anomalies / total_logs * 100, 2) if total_logs > 0 else 0.0

        # Les 3 types d'attaques récurrentes à ce jour
        top_types = [
            {"type": row[0], "nb": row[1]}
            for row in conn.execute("""
                SELECT type_attaque, COUNT(*) AS nb
                FROM anomalies
                WHERE date_detection LIKE ? AND type_attaque IS NOT NULL
                GROUP BY type_attaque ORDER BY nb DESC LIMIT 3
            """, (f"{jour}%",)).fetchall()
        ]

        # Les 3 types d'IPs sources récurrentes à ce jour
        top_ips = [
            {"ip": row[0], "nb": row[1]}
            for row in conn.execute("""
                SELECT ip_source, COUNT(*) AS nb
                FROM anomalies
                WHERE date_detection LIKE ? AND ip_source IS NOT NULL
                GROUP BY ip_source ORDER BY nb DESC LIMIT 3
            """, (f"{jour}%",)).fetchall()
        ]

        conn.execute("""
            INSERT OR REPLACE INTO statistiques (
                date_snapshot, total_logs, total_anomalies, taux_anomalies,
                nb_low, nb_medium, nb_high,
                score_moyen, score_max, score_min,
                top_types_attaques, top_ips_sources
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jour,
            total_logs,
            total_anomalies,
            taux,
            stats[4] or 0,
            stats[5] or 0,
            stats[6] or 0,
            round(float(stats[1]), 6) if stats[1] else 0.0,
            round(float(stats[2]), 6) if stats[2] else 0.0,
            round(float(stats[3]), 6) if stats[3] else 0.0,
            json.dumps(top_types),
            json.dumps(top_ips),
        ))

    conn.commit()
    print(f"On compte {len(jours)} snapshots calculés et insérés.")



# Génération des alertes

# Génère des alertes automatiques quand le taux d'anomalies dépasse un seuil 
def generer_alertes(conn: sqlite3.Connection) -> None:
    seuil_warning  = 30.0
    seuil_critical = 50.0
    jours = conn.execute("SELECT * FROM statistiques ORDER BY date_snapshot").fetchall()

    nb_alertes = 0
    for row in jours:
        date_snapshot   = row[1]
        total_anomalies = row[3]
        taux  = row[4]

        if taux >= seuil_critical:
            niveau = "critical"
            raison = f"Taux d'anomalies critique : {taux:.1f}% ({total_anomalies} attaques)"
        elif taux >= seuil_warning:
            niveau = "warning"
            raison = f"Taux d'anomalies élevé : {taux:.1f}% ({total_anomalies} attaques)"
        else:
            continue  # pas d'alerte si en dessous du seuil

        conn.execute("""
            INSERT INTO alertes (date_alerte, niveau, raison, taux_anomalies, nb_anomalies)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"{date_snapshot} 00:00:00",
            niveau,
            raison,
            taux,
            total_anomalies,
        ))
        nb_alertes += 1

    conn.commit()
    print(f"On compte {nb_alertes} alerte(s) générée(s).")



# Résumé final
#Affiche un résumé de ce qui a été inséré dans la base
def afficher_resume(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    total_logs   = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    total_anom   = conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]
    total_stats  = conn.execute("SELECT COUNT(*) FROM statistiques").fetchone()[0]
    total_alerts = conn.execute("SELECT COUNT(*) FROM alertes").fetchone()[0]

    print(f"  logs          : {total_logs:>10,} lignes")
    print(f"  anomalies     : {total_anom:>10,} lignes")
    print(f"  statistiques  : {total_stats:>10,} snapshots")
    print(f"  alertes       : {total_alerts:>10,} alertes")

    print("\nRépartition par dataset :")
    for row in conn.execute("SELECT dataset_source, COUNT(*) AS nb FROM logs GROUP BY dataset_source").fetchall():
        print(f"  {row[0]:<15} : {row[1]:>10,} logs")

    print("\nRépartition des anomalies par sévérité :")
    for row in conn.execute("SELECT severite, COUNT(*) AS nb FROM anomalies GROUP BY severite").fetchall():
        print(f"  {row[0]:<10} : {row[1]:>10,}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from schema import schema_log, schema_anomalie, schema_stat, schema_alerte, index  # ← ajoute cette ligne

    mode_test = "--test" in sys.argv
    limite = 5000 if mode_test else None

    if mode_test:
        print("On test seulement 5000 lignes par dataset\n")

    print(f"Base de données : {db_path}\n")
    conn = sqlite3.connect(db_path)  # ← conn est créé ici

    # crée les tables si elles n'existent pas
    conn.executescript(schema_log)
    conn.executescript(schema_anomalie)
    conn.executescript(schema_stat)
    conn.executescript(schema_alerte)
    conn.executescript(index)

    try:
        pipeline, detecteur, params = charger_modele()
        traiter_unsw(conn, pipeline, detecteur, params, limite=limite)
        traiter_cicids(conn, pipeline, detecteur, params, limite=limite)
        traiter_logs_clean(conn, limite=limite)
        calculer_statistiques(conn)
        generer_alertes(conn)
        afficher_resume(conn)
    except Exception as e:
        conn.rollback()
        print(f"\nErreur : {e}")
        raise
    finally:
        conn.close()
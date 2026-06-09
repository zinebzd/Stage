"""
Ce fichier a pour but de définir la structure des 4 tables en SQL.C'est le plan de la base de données. 
Il ne crée rien tout seul il est juste lu par migration_001 qui lui envoie les instructions SQL à la base.

Il y a 4 tables :
- anomalies : stocke chaque flux réseau classé comme attaque par le modèle
- logs : stocke les logs bruts des fichiers cicids et unsw avant analyse
- statistiques : stocke des résumés calculés périodiquement (nb attaques, scores moyens...)
- alertes : stocke les alertes critiques déclenchées quand le danger est élevé

Chaque table a un id auto-incrémenté et une date de création.
"""

# Schéma SQL de chaque table qui sera utilisé par les migrations

schema_anomalie = """
CREATE TABLE IF NOT EXISTS anomalies (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id            INTEGER,
    date_detection    TEXT,
    ip_source         TEXT,
    ip_destination    TEXT,
    protocole         TEXT,
    type_attaque      TEXT,
    severite          TEXT,
    score_anomalie    REAL,
    dataset_source    TEXT,
    FOREIGN KEY (log_id) REFERENCES logs(id)
);
"""

schema_log = """
CREATE TABLE IF NOT EXISTS logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    analyse           TEXT,       -- date d'analyse du flux
    ip_source         TEXT,       -- adresse IP source
    ip_destination    TEXT,       -- adresse IP destination
    protocole         TEXT,       -- TCP, UDP, ICMP...
    port_destination  INTEGER,    -- port destination
    score_anomalie    REAL,       -- score MSE retourné par l'autoencoder
    prediction        INTEGER,    -- 0 = normal, 1 = attaque
    severite          TEXT,       -- low, medium, high (NULL si normal)
    dataset_source    TEXT,       -- cicids, unsw ou logs_clean
    type_attaque      TEXT,       -- DDoS, DoS, Exploits... (NULL si normal)
    action            TEXT,       -- allowed ou blocked
    log_type          TEXT,       -- firewall, ids, application...
    bytes_transferes  INTEGER     -- volume de données transférées
);
"""

schema_stat = """
CREATE TABLE IF NOT EXISTS statistiques (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date_snapshot     TEXT UNIQUE, -- jour du snapshot (YYYY-MM-DD)
    total_logs        INTEGER,     -- nombre total de flux ce jour
    total_anomalies   INTEGER,     -- nombre d'attaques détectées ce jour
    taux_anomalies    REAL,        -- pourcentage d'attaques (0-100)
    nb_low            INTEGER,     -- nombre d'anomalies de sévérité low
    nb_medium         INTEGER,     -- nombre d'anomalies de sévérité medium
    nb_high           INTEGER,     -- nombre d'anomalies de sévérité high
    score_moyen       REAL,        -- score MSE moyen ce jour
    score_max         REAL,        -- score MSE maximum ce jour
    score_min         REAL,        -- score MSE minimum ce jour
    top_types_attaques TEXT,       -- JSON : top 3 types d'attaques du jour
    top_ips_sources   TEXT         -- JSON : top 3 IPs sources du jour
);
"""

schema_alerte = """
CREATE TABLE IF NOT EXISTS alertes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_alerte     TEXT,       -- date de déclenchement de l'alerte
    niveau          TEXT,       -- warning ou critical
    raison          TEXT,       -- description lisible de l'alerte
    taux_anomalies  REAL,       -- taux d'anomalies ayant déclenché l'alerte
    nb_anomalies    INTEGER     -- nombre d'anomalies concernées
);
"""

# Index pour accélérer les requêtes fréquentes
index = """
CREATE INDEX IF NOT EXISTS idx_anomalies_date     ON anomalies(date_detection);
CREATE INDEX IF NOT EXISTS idx_anomalies_severite ON anomalies(severite);
CREATE INDEX IF NOT EXISTS idx_anomalies_source   ON anomalies(dataset_source);
CREATE INDEX IF NOT EXISTS idx_anomalies_ip       ON anomalies(ip_source);
CREATE INDEX IF NOT EXISTS idx_logs_source        ON logs(dataset_source);
CREATE INDEX IF NOT EXISTS idx_logs_date          ON logs(analyse);
CREATE INDEX IF NOT EXISTS idx_logs_prediction    ON logs(prediction);
CREATE INDEX IF NOT EXISTS idx_stats_date         ON statistiques(date_snapshot);
CREATE INDEX IF NOT EXISTS idx_alertes_niveau     ON alertes(niveau);
"""


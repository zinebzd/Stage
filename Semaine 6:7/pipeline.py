"""
Jusqu'ici dans des notebooks on a effectué le chargement des données, nettoyage, normalisation, entraînement du modèle, détection.
Maintenant le but est que si quelqu'un veut utiliser le modèle sur de nouvelles données, il ne peut pas exécuter un notebook entier.
L'idée du pipeline est de connecter toutes ces étapes dans un seul fichier structuré.

1 - Ingestion pour charger un fichier CSV de trafic réseau
2- Preprocessing pour nettoyer et normaliser les données 
3- Feature engineering pour créer des features supplémentaires utiles
4- Prédiction pour passer les données dans l'autoencoder
5- Score d'anomalie 
"""
# %%
import random
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

random.seed(42)
np.random.seed(42)
tf.random.set_seed(42)



# %%
# 1 - Ingestion

def ingestion(chemin: str, label_col: str = 'label', normal_val=0) -> tuple:
    df = pd.read_csv(chemin, low_memory=False)
    cols_lower = {c.lower(): c for c in df.columns} # détection automatique du nom exact de la colonne label 
    label_col  = cols_lower.get(label_col.lower(), label_col)
    y = (df[label_col] != normal_val).astype(int)  # 0 pour normal et 1 pour attaque
    X = df.drop(columns=[label_col]).select_dtypes(include=[np.number])  # features numériques uniquement
    print(f"[Ingestion] {len(df)} lignes , {X.shape[1]} features et  {y.mean():.1%} attaques")
    return X, y





# %%

# 2-Preprocessing
class Preprocesseur(BaseEstimator, TransformerMixin):
    
    def __init__(self):
        self.scaler = StandardScaler() # normalisation permet de centré et réduire chaque feature


    def fit(self, X, y=None): # apprend la moyenne et l'écart-type sur les données normales uniquement
        X_clean = self._nettoyer(X)
        self.scaler.fit(X_clean)
        self.is_fitted_ = True  
        return self

    def transform(self, X, y=None):  #nettoie les données puis applique la normalisation apprise pendant le fit, chaque feature est centrée réduite 
        X_clean = self._nettoyer(X)
        return self.scaler.transform(X_clean)

    def _nettoyer(self, X):#remplace les valeurs NaN (données manquantes) et les valeurs infinies par 0.
        return X.fillna(0).replace([np.inf, -np.inf], 0)

# %%
# 3- Feature engineering 
#La classe crée de nouvelles features à partir des colonnes existantes pour aider le modèle à mieux détecter les anomalies.
# Elle est compatible sklearn donc elle s'intègre dans le Pipeline

class FeatureEngineer(BaseEstimator, TransformerMixin):

    def __init__(self, col_src_bytes=None, col_dst_bytes=None, col_duration=None): #initialise les indices à None
        self.col_src = col_src_bytes  # indice colonne bytes source 
        self.col_dst = col_dst_bytes  # indice colonne bytes destination
        self.col_dur = col_duration   # indice colonne durée
    
    def _find(self, cols, candidates): #cherche si une colonne existe dans le dataset par plusieurs noms possibles 
        for c in candidates:       # parcourt les noms candidats possibles
            if c in cols:          # si le nom existe dans les colonnes du dataset
                return cols.index(c)  # retourne son indice
        return None                # colonne qui est introuvable

    def fit(self, X, y=None): #détecte automatiquement quelles colonnes utiles existent dans le dataset et mémorise leurs indices
        if isinstance(X, np.ndarray):   # si X est un array numpy 
            self._has_features = False  # on ne peut pas chercher les colonnes
            return self
        cols = [c.lower() for c in X.columns]  # noms en minuscules pour la recherche
        self.col_src = self._find(cols, ['sbytes', 'src_bytes', 'totlen_fwd'])   # cherche bytes source
        self.col_dst = self._find(cols, ['dbytes', 'dst_bytes', 'totlen_bwd'])   # cherche bytes destination
        self.col_dur = self._find(cols, ['dur', 'duration', 'flow_duration'])    # cherche durée
        self._has_features = True
        self._orig_cols    = list(X.columns)  # mémorise les noms originaux pour le transform
        return self

    def transform(self, X, y=None): #crée 3 nouvelles features 
        if not self._has_features or isinstance(X, np.ndarray):
            return X        # aucune colonne trouvée on retourne X sans modification
        X = X.copy()        # on ne modifie pas le DataFrame original
        if self.col_src and self.col_dst:
            denom = X[self._orig_cols[self.col_dst]] + 1e-6      # évite la division par zéro
            X['ratio_bytes'] = X[self._orig_cols[self.col_src]] / denom  # ratio bytes envoyés par reçus 
        if self.col_dur:
            X['log_duration'] = np.log1p(X[self._orig_cols[self.col_dur]].abs())       # log(durée+1) réduit l'impact des valeurs extrêmes
            X['short_conn']   = (X[self._orig_cols[self.col_dur]] < 0.01).astype(int)  # 1 si connexion très courte donc scan potentiel
        return X



# %%
# 4- Autoencodeur

# Construit l'architecture de l'autoencoder (32→8→32)
def build_autoencoder(input_dim: int) -> keras.Model:
    inputs  = keras.Input(shape=(input_dim,))
    x = layers.Dense(32, activation='relu')(inputs)  # encodeur
    x = layers.Dense(8, activation='relu')(x)       # espace latent
    x  = layers.Dense(32, activation='relu')(x)       # décodeur
    outputs = layers.Dense(input_dim, activation='linear')(x)
    model = keras.Model(inputs, outputs)
    model.compile(optimizer='adam', loss='mse')
    return model


class AutoencoderDetecteur(BaseEstimator):

    def __init__(self, seuil=0.302, epochs=30, batch_size=256):
        self.seuil  = seuil       # seuil opérationnel retenu
        self.epochs = epochs
        self.batch_size = batch_size

    def fit(self, X_train, y=None):  # construit et entraîne le modèle sur le trafic normal uniquement
        self.model_ = build_autoencoder(X_train.shape[1])
        self.model_.fit(X_train, X_train,epochs=self.epochs,batch_size=self.batch_size,validation_split=0.1,verbose=0)
        print(f"Autoencoder entraîné sur {len(X_train)} flux avec {X_train.shape[1]} features")
        return self

    def score_anomalie(self, X) -> np.ndarray:  #erreur MSE qui est le score anomalie
        recons = self.model_.predict(X, verbose=0)
        return np.mean((X - recons) ** 2, axis=1)

    def predict(self, X) -> np.ndarray:  #1 si le score dépasse le seuil donc anomalie et 0 sinon pour normal
        return (self.score_anomalie(X) > self.seuil).astype(int) 



# %%
# 5-Prédiction
#Pipeline sklearn donc nettoyage (NaN, inf) et normalisation StandardScaler

def construire_pipeline(seuil: float = 0.302) -> tuple:
    pipe = Pipeline([('preprocessing', Preprocesseur())])
    detecteur = AutoencoderDetecteur(seuil=seuil) # le détecteur est séparé du Pipeline car l'autoencoder s'entraîne avec fit(X, X)
    return pipe, detecteur   #on retourne les deux séparément pour les utiliser dans le main


# %%
# 6 - Score anomalie

def evaluer(y_test, pred, scores):
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel() #extrait les 4 valeurs de la matrice de confusion
    print(f" AUC-ROC : {roc_auc_score(y_test, scores):.4f}")
    print(f" Précision : {precision_score(y_test, pred, zero_division=0):.4f}")
    print(f" Recall : {recall_score(y_test, pred, zero_division=0):.4f}")
    print(f" f1-score  : {f1_score(y_test, pred, zero_division=0):.4f}")
    print(f" Attaques détectées : {tp}")
    print(f" Fausses alertes: {fp}")
    print(f" Attaques ratées: {fn}")
    print(f" Normaux corrects : {tn}")

# %%
# 7- Exécution 

if __name__ == "__main__":
    
    chemin= "../Data/unsw_clean.csv"
    seuil = 0.302  # seuil opérationnel retenu (max F1)

    # Ingestion on charge le CSV et retourne X et y
    X, y = ingestion(chemin, label_col='label', normal_val=0)

    # Séparation normal/attaque
    X_normal  = X[y == 0]
    X_attaque = X[y == 1]
    X_train_raw, X_test_normal_raw = train_test_split(X_normal, test_size=0.2, random_state=42)

    # Construction du jeu de test équilibré : 50% normaux + 50% attaques
    n = len(X_test_normal_raw)
    idx = np.random.choice(len(X_attaque), size=min(n, len(X_attaque)), replace=False)
    X_test_raw = pd.concat([X_test_normal_raw, X_attaque.iloc[idx]])
    y_test = np.array([0] * n + [1] * len(idx))

    # Preprocessing 
    pipe, detecteur = construire_pipeline(seuil=seuil)
    X_train = pipe.fit_transform(X_train_raw)  # fit + transform en une seule ligne
    X_test  = pipe.transform(X_test_raw)
    # Entraînement de l'autoencoder sur le trafic normal
    detecteur.fit(X_train)

    # Prédiction et score d'anomalie sur le jeu de test
    scores = detecteur.score_anomalie(X_test)
    pred = detecteur.predict(X_test)

    print(f"\n Seuil opérationnel : {seuil}")
    print(f"Score moyen normaux : {scores[y_test==0].mean():.4f}")
    print(f"Score moyen attaques : {scores[y_test==1].mean():.4f}")

    # Évaluation finale
    evaluer(y_test, pred, scores)


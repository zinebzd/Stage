# Shim de compatibilité : le modèle joblib a été sauvegardé avec l'ancien chemin
# de module "pipeline". Ce fichier redirige vers models.pipeline pour que
# la désérialisation pickle fonctionne.
from models.pipeline import *  # noqa: F401, F403
from models.pipeline import AutoencoderDetecteur, Preprocesseur, construire_autoencoder, construire_pipeline

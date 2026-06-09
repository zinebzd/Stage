"""
Fonctions utilitaires partagées par le reste du projet
"""


def calculer_severite(score: float) -> str:
    if score < 1.0:
        return "low"
    elif score < 10.0:
        return "medium"
    else:
        return "high"

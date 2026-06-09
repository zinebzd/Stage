#!/usr/bin/env bash
# Met en place l'environnement virtuel et installe les dépendances.
# Usage : bash setup.sh

set -e

echo "==> Création du venv Python..."
python3.11 -m venv .venv

echo "==> Activation du venv..."
source .venv/bin/activate

echo "==> Mise à jour de pip..."
pip install --upgrade pip

echo "==> Installation des dépendances..."
pip install -r requirements.txt

echo ""
echo "✓ Environnement prêt."
echo ""
echo "Commandes utiles :"
echo "  source .venv/bin/activate                        # activer le venv"
echo "  uvicorn api.app:app --reload --port 8000         # lancer l'API"
echo "  pytest tests/ -v                                 # lancer les tests"
echo "  deactivate                                       # désactiver le venv"

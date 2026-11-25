"""
Zentrale Konfiguration für den Lunch Planner.
Erkennt automatisch, ob die App auf PythonAnywhere oder lokal läuft.
"""

import os

# Basispfad (funktioniert sowohl lokal als auch auf PythonAnywhere)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Datenverzeichnisse (alle relativ zum Projektordner)
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVED_PLANS_DIR = os.path.join(BASE_DIR, "saved_plans")

# Verzeichnisse erstellen, falls nicht vorhanden
for d in [DATA_DIR, SAVED_PLANS_DIR]:
    os.makedirs(d, exist_ok=True)

# Erkennung: Läuft die App auf PythonAnywhere?
ON_PYTHONANYWHERE = "PYTHONANYWHERE_SITE" in os.environ

# Debug-Modus (aus auf PythonAnywhere, an bei lokaler Entwicklung)
DEBUG = not ON_PYTHONANYWHERE

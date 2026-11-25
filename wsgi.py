"""
WSGI-Konfigurationsdatei für PythonAnywhere.

Anleitung:
  1. In der PythonAnywhere Web-Konfiguration die WSGI-Datei bearbeiten.
  2. Den gesamten Inhalt der automatisch erstellten Datei durch diesen Code ersetzen.
  3. Den Benutzernamen (DEIN_BENUTZERNAME) anpassen.
"""

import sys
import os

# ── Benutzername hier anpassen ───────────────────────────────────────────
USERNAME = "DEIN_BENUTZERNAME"  # ← PythonAnywhere-Benutzername eintragen!
# ─────────────────────────────────────────────────────────────────────────

# Projektverzeichnis (absoluter Pfad auf PythonAnywhere)
PROJECT_DIR = f"/home/{USERNAME}/lunch_planner"

# Virtualenv Pfad (falls genutzt)
VENV_DIR = f"/home/{USERNAME}/.virtualenvs/lunchplanner/lib/python3.10/site-packages"

# Projekt zum Python-Pfad hinzufügen
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Virtualenv-Pakete hinzufügen (falls vorhanden)
if os.path.exists(VENV_DIR):
    sys.path.insert(0, VENV_DIR)

# Flask-App importieren
from app import app as application  # noqa: E402

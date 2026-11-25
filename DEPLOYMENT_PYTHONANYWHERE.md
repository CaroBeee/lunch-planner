# 🚀 Deployment auf PythonAnywhere – Schritt-für-Schritt-Anleitung

Diese Anleitung beschreibt, wie der **7-Tage Mittagsplaner** kostenlos auf
[PythonAnywhere](https://www.pythonanywhere.com) gehostet wird.

---

## Übersicht

| Eigenschaft | Wert |
|---|---|
| Hosting | PythonAnywhere Free-Tier |
| URL | `https://DEIN_BENUTZERNAME.pythonanywhere.com` |
| Kosten | 0 € (Free-Tier) |
| Python-Version | 3.10 (empfohlen) |
| Framework | Flask (WSGI) |
| Spoonacular API | ✅ funktioniert (ist whitelisted) |

---

## Schritt 1 – Account erstellen

1. Gehe zu [https://www.pythonanywhere.com/registration/register/beginner/](https://www.pythonanywhere.com/registration/register/beginner/)
2. Erstelle einen **kostenlosen Beginner-Account**
3. Wähle einen Benutzernamen – dieser wird Teil der URL:
   `https://DEIN_BENUTZERNAME.pythonanywhere.com`

> 💡 **Tipp:** Wähle einen kurzen, einprägsamen Namen (z. B. `familieplaner`).

---

## Schritt 2 – Code hochladen

### Option A: Über Git (empfohlen)

1. Öffne ein **Bash-Terminal** auf PythonAnywhere:
   → Dashboard → "Consoles" → "Bash"

2. Klone das Repository:
   ```bash
   cd ~
   git clone https://github.com/DEIN_REPO/lunch_planner.git
   ```

### Option B: Manueller Upload

1. Gehe zu **"Files"** im PythonAnywhere-Dashboard
2. Navigiere zu `/home/DEIN_BENUTZERNAME/`
3. Erstelle den Ordner `lunch_planner`
4. Lade folgende Dateien/Ordner hoch:
   ```
   lunch_planner/
   ├── app.py
   ├── planner_logic.py
   ├── requirements.txt
   ├── wsgi.py
   ├── data/
   │   ├── fixDishes.json
   │   ├── spoonacular_exclude_list.json
   │   └── spoonacular_ingredients.json
   ├── templates/
   │   └── index.html
   └── static/
       ├── css/style.css
       └── js/app.js
   ```

> ⚠️ **Wichtig:** PythonAnywhere erlaubt nur einzelne Datei-Uploads über die
> Web-Oberfläche. Für mehrere Dateien empfiehlt sich eine ZIP-Datei, die du
> dann im Bash-Terminal entpackst:
> ```bash
> cd ~
> unzip lunch_planner.zip
> ```

---

## Schritt 3 – Virtual Environment erstellen

1. Öffne ein **Bash-Terminal**:
   → Dashboard → "Consoles" → "Bash"

2. Erstelle ein Virtual Environment:
   ```bash
   mkvirtualenv lunchplanner --python=/usr/bin/python3.10
   ```

3. Das Virtual Environment wird automatisch aktiviert. Du siehst:
   ```
   (lunchplanner) $
   ```

---

## Schritt 4 – Dependencies installieren

```bash
cd ~/lunch_planner
pip install -r requirements.txt
```

Das installiert:
- Flask
- requests
- deep-translator
- openpyxl

---

## Schritt 5 – Web-App konfigurieren

1. Gehe zu **"Web"** im Dashboard
2. Klicke auf **"Add a new web app"**
3. Wähle **"Manual configuration"** (NICHT "Flask"!)
4. Wähle **Python 3.10**

### 5a – WSGI-Datei bearbeiten

1. Auf der Web-Seite findest du den Link zur **WSGI configuration file**
   (z. B. `/var/www/DEIN_BENUTZERNAME_pythonanywhere_com_wsgi.py`)
2. Klicke auf den Link und **lösche den gesamten Inhalt**
3. Ersetze ihn durch folgenden Code:

```python
import sys
import os

# ── Benutzername hier anpassen ──
USERNAME = "DEIN_BENUTZERNAME"  # ← deinen PythonAnywhere-Benutzernamen eintragen!

PROJECT_DIR = f"/home/{USERNAME}/lunch_planner"
VENV_DIR = f"/home/{USERNAME}/.virtualenvs/lunchplanner/lib/python3.10/site-packages"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

if os.path.exists(VENV_DIR):
    sys.path.insert(0, VENV_DIR)

from app import app as application
```

4. **Speichern** (grüner Button oben rechts)

### 5b – Virtualenv-Pfad eintragen

Auf der **Web**-Seite unter **"Virtualenv"**:
```
/home/DEIN_BENUTZERNAME/.virtualenvs/lunchplanner
```

### 5c – Source Code Pfad eintragen

Unter **"Source code"**:
```
/home/DEIN_BENUTZERNAME/lunch_planner
```

---

## Schritt 6 – Statische Dateien konfigurieren

Auf der **Web**-Seite unter **"Static files"** zwei Einträge hinzufügen:

| URL | Directory |
|---|---|
| `/static/css` | `/home/DEIN_BENUTZERNAME/lunch_planner/static/css` |
| `/static/js` | `/home/DEIN_BENUTZERNAME/lunch_planner/static/js` |

Alternativ einen einzigen Eintrag:

| URL | Directory |
|---|---|
| `/static` | `/home/DEIN_BENUTZERNAME/lunch_planner/static` |

> 💡 Statische Dateien werden so direkt vom Webserver ausgeliefert –
> schneller als über Flask.

---

## Schritt 7 – Datenordner erstellen

Falls noch nicht vorhanden, erstelle die Ordner im Bash-Terminal:

```bash
cd ~/lunch_planner
mkdir -p data cache saved_plans
```

---

## Schritt 8 – JSON-Dateien prüfen

Stelle sicher, dass folgende Dateien im `data/`-Ordner vorhanden sind:

```bash
ls -la ~/lunch_planner/data/
```

Erwartete Dateien:
- `fixDishes.json` – Feste Familiengerichte
- `spoonacular_exclude_list.json` – Ausschlussliste
- `spoonacular_ingredients.json` – Zutatenkategorien

> Falls Dateien fehlen, lade sie über die Files-Seite hoch oder kopiere sie
> aus dem Git-Repository.

---

## Schritt 9 – App starten und testen

1. Gehe zur **Web**-Seite im Dashboard
2. Klicke auf den grünen Button **"Reload"**
3. Öffne deine App: `https://DEIN_BENUTZERNAME.pythonanywhere.com`

### Erste Tests:
- [ ] Startseite wird angezeigt
- [ ] "Neuer Plan" generiert einen Wochenplan
- [ ] "API aktualisieren" ruft Spoonacular auf (dauert 10–20 Sek.)
- [ ] Plan speichern und laden funktioniert
- [ ] Gerichte tauschen funktioniert

---

## Troubleshooting – Häufige Fehler und Lösungen

### ❌ "Something went wrong" / 500 Error

**Ursache:** Fehler im Python-Code oder fehlende Abhängigkeiten.

**Lösung:**
1. Prüfe die **Error Logs** auf der Web-Seite:
   → Web → "Error log" Link (ganz unten)
2. Häufige Ursachen:
   - Fehlende Python-Pakete → `pip install -r requirements.txt`
   - Falscher Pfad in der WSGI-Datei → Benutzernamen prüfen
   - Fehlende JSON-Dateien in `data/`

### ❌ "ModuleNotFoundError: No module named 'flask'"

**Ursache:** Virtual Environment nicht korrekt eingerichtet.

**Lösung:**
1. Prüfe den Virtualenv-Pfad auf der Web-Seite
2. Im Bash-Terminal:
   ```bash
   workon lunchplanner
   pip install -r ~/lunch_planner/requirements.txt
   ```
3. Web-App neu laden ("Reload")

### ❌ Statische Dateien (CSS/JS) laden nicht

**Ursache:** Static Files Mapping fehlt oder falscher Pfad.

**Lösung:**
1. Prüfe die Static Files Konfiguration auf der Web-Seite
2. Stelle sicher, dass die Pfade korrekt sind (Benutzername!)
3. Web-App neu laden

### ❌ "FileNotFoundError" für JSON-Dateien

**Ursache:** Daten-Dateien fehlen im `data/`-Ordner.

**Lösung:**
```bash
ls ~/lunch_planner/data/
```
Falls leer, Dateien erneut hochladen.

### ❌ Spoonacular API gibt Fehler zurück

**Ursache:** API-Key ungültig oder Kontingent aufgebraucht.

**Lösung:**
1. Die Spoonacular API ist auf PythonAnywhere **whitelisted** → kein Proxy nötig
2. Prüfe den API-Key in `planner_logic.py`
3. Bei Quota-Fehler: Am nächsten Tag erneut versuchen

### ❌ Seite lädt sehr langsam

**Ursache:** Free-Tier hat begrenzte CPU-Ressourcen.

**Lösung:**
- Erste Anfrage nach Neustart ist immer langsam (Cold Start)
- API-Cache nutzen statt häufiger API-Aufrufe
- Seite nach 3 Monaten erneuern (Free-Tier läuft alle 3 Monate ab)

### ❌ "Your web app has been disabled"

**Ursache:** Free-Tier-Apps werden nach 3 Monaten Inaktivität deaktiviert.

**Lösung:**
1. Einloggen auf PythonAnywhere
2. Web-Seite → "Reload" klicken
3. Auf den "Run until 3 months from today"-Button klicken

---

## Free-Tier Einschränkungen

| Einschränkung | Details |
|---|---|
| **Domain** | Nur `BENUTZERNAME.pythonanywhere.com` |
| **HTTPS** | ✅ Standardmäßig aktiviert |
| **CPU** | Begrenzte tägliche CPU-Sekunden (~100s) |
| **Bandbreite** | Ausreichend für Familien-Nutzung |
| **Outbound HTTP** | Nur whitelisted APIs (Spoonacular ✅, Google Translate ✅) |
| **Speicher** | 512 MB Dateispeicher |
| **Ablauf** | Alle 3 Monate manuell verlängern |
| **Web-Apps** | 1 Web-App pro Free-Account |
| **Datenbank** | MySQL verfügbar (wird hier nicht benötigt) |

> 💡 Für diese App reicht der Free-Tier **vollkommen aus** – es ist ein
> Familienprojekt mit wenigen Zugriffen.

---

## Updates einspielen

### Via Git:
```bash
cd ~/lunch_planner
git pull
```
Danach Web-App neu laden ("Reload").

### Manuell:
1. Geänderte Dateien über Files-Seite hochladen
2. Web-App neu laden ("Reload")

---

## Nützliche Links

- [PythonAnywhere Dashboard](https://www.pythonanywhere.com/dashboard/)
- [PythonAnywhere Help – Flask](https://help.pythonanywhere.com/pages/Flask/)
- [PythonAnywhere Help – Static Files](https://help.pythonanywhere.com/pages/StaticFiles/)
- [PythonAnywhere Help – Debugging](https://help.pythonanywhere.com/pages/DebuggingImportError/)
- [Spoonacular API Docs](https://spoonacular.com/food-api/docs)

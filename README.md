# 🍽️ Mittagsplaner für 7 Tage

A self-hostable **7-day family lunch planner** built with Python Flask. Designed for families with a focus on simplicity, variety, and easy deployment.

## Features

- **Weekly Plan Generation** – Generates a balanced 7-day plan (Mon–Sun)
  - Diet distribution: 2–3× Meat, 1× Fish, 3–4× Veggie/Vegan
  - Weekdays: max 45 min prep time
  - Weekends: no time restriction
  - No duplicate dishes within one week
- **Swap Dishes** – Replace individual days with fixed dishes or free cards
- **Free Cards** – For eating out, leftovers, or custom entries
- **Recipe Builder** – Create and manage your own fixed dishes
- **Save & Load Plans** – Plans stored as JSON files with date and name
- **Responsive Design** – Optimized for mobile, tablet, and desktop
- **No External Database** – All data stored in JSON files

## Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone or download the project
cd lunch_planner

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open `http://localhost:5000` in your browser.

### First Steps

1. Add your own dishes under **"Einstellungen"**
2. Click **"Neuer Plan"** to generate your first weekly plan
3. Use **"Tauschen"** to swap individual dishes
4. **"Plan speichern"** to save the current plan

## Project Structure

```
lunch_planner/
├── app.py                  # Flask application (routes)
├── planner_logic.py        # Core planning logic
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── data/
│   ├── fixDishes.json              # Fixed family recipes
│   └── ingredients.json           # Local ingredient catalog for the recipe builder
├── saved_plans/
│   └── plan_YYYY-MM-DD_HHMMSS_ffffff.json  # Saved meal plans
├── templates/
│   └── index.html                  # Main HTML template
└── static/
    ├── css/
    │   └── style.css               # Responsive styles
    └── js/
        └── app.js                  # Frontend JavaScript
```

## Deployment auf PythonAnywhere (empfohlen)

Der einfachste Weg, die App öffentlich erreichbar zu machen:

1. Kostenlosen Account erstellen auf [pythonanywhere.com](https://www.pythonanywhere.com)
2. Code hochladen (Git oder ZIP-Upload)
3. Virtual Environment & Dependencies installieren
4. WSGI-Datei konfigurieren (Vorlage: `wsgi.py`)
5. Statische Dateien konfigurieren

➡️ **Detaillierte Anleitung:** Siehe [`DEPLOYMENT_PYTHONANYWHERE.md`](DEPLOYMENT_PYTHONANYWHERE.md)
➡️ **Kurzreferenz:** Siehe [`pythonanywhere_setup.txt`](pythonanywhere_setup.txt)

**Free-Tier Vorteile:**
- ✅ Kostenlos (0 €)
- ✅ HTTPS standardmäßig
- ⚠️ Muss alle 3 Monate verlängert werden

## Alternatives Deployment (FTP/Server)

1. Upload the entire `lunch_planner/` folder to your server
2. Install Python 3.8+ and pip on the server
3. Run `pip install -r requirements.txt`
4. For production, use a WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

5. Set up a reverse proxy (nginx/Apache) if needed:

```nginx
# Example nginx config
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Configuration

Edit `data/fixDishes.json` to add or modify fixed family recipes. Diet types
and preparation times are configured per dish.

## Tech Stack

- **Backend**: Python Flask
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **Font**: Nunito (Google Fonts)
- **Storage**: JSON files (no database)

## License

Private family project – no external distribution intended.

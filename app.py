"""
Lunch Planner - 7-Day Family Meal Planner
Flask backend for meal planning
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request

from planner_logic import (
    generate_weekly_plan,
    get_swap_candidates,
    load_fixed_dishes,
    get_current_week_dates,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVED_PLANS_DIR = os.path.join(BASE_DIR, "saved_plans")
INGREDIENTS_FILENAME = "ingredients.json"
LEGACY_INGREDIENTS_FILENAME = "spoonacular_ingredients.json"

for d in [DATA_DIR, SAVED_PLANS_DIR]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routes – Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API – Plan generation
# ---------------------------------------------------------------------------

@app.route("/api/generate", methods=["POST"])
def api_generate_plan():
    """Generate a new 7-day lunch plan."""
    try:
        body = request.get_json(silent=True) or {}
        free_days = body.get("free_days", [])  # list of day indices 0-6 for free cards
        week_offset = int(body.get("week_offset", 0))

        plan = generate_weekly_plan(
            DATA_DIR,
            free_days=free_days,
            week_offset=week_offset,
        )
        return jsonify({"success": True, "plan": plan})
    except Exception as e:
        logger.exception("Error generating plan")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# API – Swap a single day
# ---------------------------------------------------------------------------

@app.route("/api/swap", methods=["POST"])
def api_swap_day():
    """Return swap candidates for a given day index."""
    try:
        body = request.get_json()
        current_titles = body.get("current_titles", [])
        candidates = get_swap_candidates(DATA_DIR, current_titles)
        return jsonify({"success": True, "candidates": candidates})
    except Exception as e:
        logger.exception("Error fetching swap candidates")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# API – Save / Load plans
# ---------------------------------------------------------------------------

@app.route("/api/plans/save", methods=["POST"])
def api_save_plan():
    """Save the current plan to a JSON file."""
    try:
        body = request.get_json()
        plan = body.get("plan", [])
        name = body.get("name", "")
        dates = body.get("dates", {})

        now = datetime.now()
        filename = f"plan_{now.strftime('%Y-%m-%d_%H%M%S_%f')}.json"
        filepath = os.path.join(SAVED_PLANS_DIR, filename)

        payload = {
            "name": name or f"Plan vom {now.strftime('%d.%m.%Y')}",
            "created": now.isoformat(),
            "dates": dates,
            "plan": plan,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        logger.exception("Error saving plan")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plans/list", methods=["GET"])
def api_list_plans():
    """List all saved plans."""
    try:
        plans = []
        for fname in sorted(os.listdir(SAVED_PLANS_DIR), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(SAVED_PLANS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                plans.append({
                    "filename": fname,
                    "name": data.get("name", fname),
                    "created": data.get("created", ""),
                    "dates": data.get("dates", {}),
                })
        plans.sort(
            key=lambda plan: (plan["created"], plan["filename"]),
            reverse=True,
        )
        return jsonify({"success": True, "plans": plans})
    except Exception as e:
        logger.exception("Error listing plans")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plans/load/<filename>", methods=["GET"])
def api_load_plan(filename):
    """Load a saved plan by filename."""
    try:
        fpath = os.path.join(SAVED_PLANS_DIR, filename)
        if not os.path.exists(fpath):
            return jsonify({"success": False, "error": "Plan nicht gefunden."}), 404
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, "plan": data.get("plan", []), "dates": data.get("dates", {}), "name": data.get("name", "")})
    except Exception as e:
        logger.exception("Error loading plan")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plans/delete/<filename>", methods=["DELETE"])
def api_delete_plan(filename):
    """Delete a saved plan."""
    try:
        fpath = os.path.join(SAVED_PLANS_DIR, filename)
        if os.path.exists(fpath):
            os.remove(fpath)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error deleting plan")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# API – Week dates helper
# ---------------------------------------------------------------------------

@app.route("/api/week-dates", methods=["GET"])
def api_week_dates():
    """Return week Monday-Sunday dates. Optional ?week_offset=1 for next week."""
    week_offset = int(request.args.get("week_offset", 0))
    dates = get_current_week_dates(week_offset)
    return jsonify({"success": True, "dates": dates})


# ---------------------------------------------------------------------------
# API – Ingredients builder
# ---------------------------------------------------------------------------

@app.route("/api/ingredients", methods=["GET"])
def api_ingredients():
    try:
        path = _ingredients_path()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, "categories": data.get("categories", [])})
    except Exception as e:
        logger.exception("Error loading ingredients")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ingredients/add", methods=["POST"])
def api_add_ingredient():
    """Add a new ingredient to a category in the local ingredient catalog."""
    try:
        body = request.get_json(silent=True) or {}
        category_key = (body.get("category") or body.get("category_key") or "").strip()
        item_name = (body.get("name") or "").strip()
        if not category_key or not item_name:
            return jsonify({"success": False, "error": "Kategorie und Name sind erforderlich."}), 400
        path = _ingredients_path()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        found = False
        for cat in data.get("categories", []):
            if cat.get("category", cat.get("key")) == category_key:
                items = cat.setdefault("items", [])
                if not any(item.get("original_de") == item_name for item in items):
                    items.append({
                        "original_de": item_name,
                        "query": item_name,
                        "alternatives": [],
                    })
                found = True
                break
        if not found:
            return jsonify({"success": False, "error": f"Kategorie '{category_key}' nicht gefunden."}), 404
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error adding ingredient")
        return jsonify({"success": False, "error": str(e)}), 500


def _ingredients_path():
    """Use the renamed catalog, or keep existing deployments on their legacy file."""
    path = os.path.join(DATA_DIR, INGREDIENTS_FILENAME)
    legacy_path = os.path.join(DATA_DIR, LEGACY_INGREDIENTS_FILENAME)
    if os.path.exists(path) or not os.path.exists(legacy_path):
        return path
    return legacy_path


# ---------------------------------------------------------------------------
# API – Fixed dishes management
# ---------------------------------------------------------------------------

@app.route("/api/fixed-dishes", methods=["GET"])
def api_get_fixed_dishes():
    """Return all fixed dishes."""
    try:
        dishes = load_fixed_dishes(DATA_DIR)
        return jsonify({"success": True, "dishes": dishes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fixed-dishes/save", methods=["POST"])
def api_save_fixed_dish():
    """Add a new fixed dish or update existing in fixDishes.json."""
    try:
        body = request.get_json(silent=True) or {}
        dish = body.get("dish", body)
        title = (dish.get("title") or "").strip()
        if not title:
            return jsonify({"success": False, "error": "Titel ist erforderlich."}), 400
        path = os.path.join(DATA_DIR, "fixDishes.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        recipes = data.get("recipes", [])
        existing_idx = next((i for i, r in enumerate(recipes) if r.get("title") == title), None)
        if existing_idx is not None:
            recipes[existing_idx] = dish
        else:
            recipes.append(dish)
        data["recipes"] = recipes
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error saving fixed dish")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fixed-dishes/delete", methods=["POST"])
def api_delete_fixed_dish():
    """Delete a fixed dish by title."""
    try:
        body = request.get_json()
        title = body.get("title", "").strip()
        path = os.path.join(DATA_DIR, "fixDishes.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["recipes"] = [r for r in data.get("recipes", []) if r.get("title") != title]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error deleting fixed dish")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

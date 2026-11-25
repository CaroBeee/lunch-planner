"""
Lunch Planner - 7-Day Family Meal Planner
Flask backend with Spoonacular API integration
"""

import os
import json
import random
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

from planner_logic import (
    generate_weekly_plan,
    get_swap_candidates,
    load_fixed_dishes,
    load_exclude_list,
    save_exclude_list,
    load_cached_recipes,
    save_cached_recipes,
    fetch_and_cache_api_recipes,
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
CACHE_DIR = os.path.join(BASE_DIR, "cache")

for d in [DATA_DIR, SAVED_PLANS_DIR, CACHE_DIR]:
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
        include_api_recipes = bool(body.get("include_api_recipes", True))

        plan = generate_weekly_plan(
            DATA_DIR,
            CACHE_DIR,
            free_days=free_days,
            week_offset=week_offset,
            include_api_recipes=include_api_recipes,
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
        day_index = body.get("day_index", 0)
        current_titles = body.get("current_titles", [])
        swap_type = body.get("swap_type", "all")  # "fixed", "api", "free", "all"

        candidates = get_swap_candidates(
            DATA_DIR, CACHE_DIR, current_titles, swap_type
        )
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
# API – Exclude list management
# ---------------------------------------------------------------------------

@app.route("/api/exclude-list", methods=["GET"])
def api_get_exclude_list():
    """Get the current exclude list."""
    try:
        data = load_exclude_list(DATA_DIR)
        return jsonify({"success": True, "exclude_rules": data.get("exclude_rules", {})})
    except Exception as e:
        logger.exception("Error loading exclude list")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/exclude-list", methods=["POST"])
def api_update_exclude_list():
    """Update the exclude list."""
    try:
        body = request.get_json()
        exclude_rules = body.get("exclude_rules", {})
        save_exclude_list(DATA_DIR, exclude_rules)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Error saving exclude list")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# API – Spoonacular cache refresh
# ---------------------------------------------------------------------------

@app.route("/api/refresh-cache", methods=["POST"])
def api_refresh_cache():
    """Manually refresh the Spoonacular recipe cache."""
    try:
        result = fetch_and_cache_api_recipes(DATA_DIR, CACHE_DIR)
        # result is now a structured dict from planner_logic
        if result.get("success"):
            return jsonify({
                "success": True,
                "cached_count": result["cached_count"],
            })
        else:
            # API error occurred – return error details to frontend
            return jsonify({
                "success": False,
                "error_type": result.get("error_type", "unknown"),
                "message": result.get("message", "Unbekannter Fehler"),
                "cached_count": result.get("cached_count", 0),
                "used_fallback": result.get("used_fallback", False),
            })
    except Exception as e:
        logger.exception("Error refreshing cache")
        return jsonify({
            "success": False,
            "error_type": "unknown",
            "message": str(e),
            "cached_count": 0,
            "used_fallback": False,
        }), 500


@app.route("/api/cache-info", methods=["GET"])
def api_cache_info():
    """Return info about the recipe cache."""
    try:
        cache_file = os.path.join(CACHE_DIR, "spoonacular_recipes.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({
                "success": True,
                "count": len(data.get("recipes", [])),
                "last_updated": data.get("last_updated", ""),
            })
        return jsonify({"success": True, "count": 0, "last_updated": ""})
    except Exception as e:
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
        path = os.path.join(DATA_DIR, "spoonacular_ingredients.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, "categories": data.get("categories", [])})
    except Exception as e:
        logger.exception("Error loading ingredients")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ingredients/add", methods=["POST"])
def api_add_ingredient():
    """Add a new ingredient to a category in spoonacular_ingredients.json."""
    try:
        body = request.get_json()
        category_key = body.get("category_key", "")
        item_name = body.get("name", "").strip()
        if not category_key or not item_name:
            return jsonify({"success": False, "error": "category_key und name sind erforderlich."}), 400
        path = os.path.join(DATA_DIR, "spoonacular_ingredients.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        found = False
        for cat in data.get("categories", []):
            if cat.get("key") == category_key:
                if item_name not in cat.get("items", []):
                    cat.setdefault("items", []).append(item_name)
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
        body = request.get_json()
        dish = body.get("dish", {})
        title = dish.get("title", "").strip()
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

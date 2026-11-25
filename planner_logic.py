"""
Core planning logic for the 7-Day Lunch Planner.
Handles plan generation, Spoonacular API integration, caching, and translation.
"""

import os
import json
import random
import logging
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPOONACULAR_API_KEY = "6a32b0d3742d4cca9a45844d09bd0e60"
SPOONACULAR_BASE = "https://api.spoonacular.com"
DAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WEEKDAY_MAX_MINUTES = 45  # max prep time on weekdays (Mon-Fri)




# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def load_fixed_dishes(data_dir):
    """Load fixed dishes from JSON file."""
    path = os.path.join(data_dir, "fixDishes.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("recipes", [])


def load_exclude_list(data_dir):
    """Load the exclude list configuration."""
    path = os.path.join(data_dir, "spoonacular_exclude_list.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_exclude_list(data_dir, exclude_rules):
    """Save updated exclude rules back to file."""
    path = os.path.join(data_dir, "spoonacular_exclude_list.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["exclude_rules"] = exclude_rules
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cached_recipes(cache_dir):
    """Load cached Spoonacular recipes."""
    path = os.path.join(cache_dir, "spoonacular_recipes.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("recipes", [])


def save_cached_recipes(cache_dir, recipes):
    """Save recipes to cache file."""
    path = os.path.join(cache_dir, "spoonacular_recipes.json")
    data = {
        "last_updated": datetime.now().isoformat(),
        "count": len(recipes),
        "recipes": recipes,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def get_current_week_dates(week_offset=0):
    """Return dict with start/end dates for the selected week (Mon-Sun).
    week_offset=0 → current week, week_offset=1 → next week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    return {
        "start": monday.strftime("%d.%m.%Y"),
        "end": sunday.strftime("%d.%m.%Y"),
        "days": [
            {
                "name": DAYS_DE[i],
                "date": (monday + timedelta(days=i)).strftime("%d.%m.%Y"),
                "is_weekend": i >= 5,
            }
            for i in range(7)
        ],
    }


# ---------------------------------------------------------------------------
# Spoonacular API helpers
# ---------------------------------------------------------------------------

def _translate_text(text):
    """Translate English text to German using free translation.
    Falls back to original text if translation fails."""
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="en", target="de")
        # Translate in chunks if text is long (limit 5000 chars)
        if len(text) > 4500:
            chunks = []
            sentences = text.split(". ")
            current = ""
            for s in sentences:
                if len(current) + len(s) > 4000:
                    chunks.append(current)
                    current = s
                else:
                    current = current + ". " + s if current else s
            if current:
                chunks.append(current)
            translated = ". ".join(translator.translate(c) for c in chunks)
            return translated
        return translator.translate(text)
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return text


def _classify_diet(recipe):
    """Classify a Spoonacular recipe into diet type."""
    if recipe.get("vegan"):
        return "vegan"
    if recipe.get("vegetarian"):
        return "vegetarian"
    # Check for fish-related keywords
    title_lower = (recipe.get("title") or "").lower()
    fish_keywords = ["salmon", "fish", "tuna", "shrimp", "prawn", "cod", "trout",
                     "lachs", "fisch", "thunfisch", "garnelen", "kabeljau", "forelle",
                     "sea bass", "halibut", "tilapia", "mahi"]
    for kw in fish_keywords:
        if kw in title_lower:
            return "fish"
    # Check ingredients for fish
    for ing in recipe.get("extendedIngredients", []):
        ing_name = (ing.get("name") or "").lower()
        for kw in fish_keywords:
            if kw in ing_name:
                return "fish"
    return "meat"


def _is_soup(recipe):
    """Check if recipe is a soup (to exclude)."""
    dish_types = recipe.get("dishTypes", [])
    title_lower = (recipe.get("title") or "").lower()
    soup_keywords = ["soup", "stew", "suppe", "eintopf"]
    if any(dt in ["soup", "stew"] for dt in dish_types):
        return True
    if any(kw in title_lower for kw in soup_keywords):
        return True
    return False


def _is_sweet_main(recipe, exclude_rules=None):
    """Check if recipe is a sweet main dish (to exclude)."""
    dish_types = [dt.lower() for dt in recipe.get("dishTypes", [])]
    title_lower = (recipe.get("title") or "").lower()
    sweet_dish_types = {"dessert", "sweet", "breakfast", "brunch"}
    if any(dt in sweet_dish_types for dt in dish_types):
        return True
    sweet_title_keywords = [
        "kaiserschmarrn", "milchreis", "pancake", "crepe", "pfannkuchen",
        "obstsalat", "fruit salad", "smoothie bowl", "french toast",
        "waffle", "waffel",
    ]
    if exclude_rules:
        sweet_title_keywords += [t.lower() for t in exclude_rules.get("excludeTitles", [])]
    if any(kw in title_lower for kw in sweet_title_keywords):
        return True
    return False


def _recipe_matches_exclude(recipe, exclude_rules):
    """Return True if recipe passes all configured exclude rules."""
    rules = exclude_rules or {}
    title = (recipe.get("title") or "").lower()

    dish_types = [str(x).lower() for x in recipe.get("dishTypes", []) if x]
    cuisines = [str(x).lower() for x in recipe.get("cuisines", []) if x]
    diets = [str(x).lower() for x in recipe.get("diets", []) if x]
    occasions = [str(x).lower() for x in recipe.get("occasions", []) if x]

    ingredient_texts = []
    for ing in recipe.get("extendedIngredients", []):
        if isinstance(ing, dict):
            ingredient_texts.append((ing.get("name") or "").lower())
            ingredient_texts.append((ing.get("original") or "").lower())
            ingredient_texts.append((ing.get("originalString") or "").lower())
        else:
            ingredient_texts.append(str(ing).lower())
    ingredient_texts += [str(x).lower() for x in recipe.get("ingredients", []) if x]
    ingredient_texts += [str(x).lower() for x in recipe.get("ingredients_en", []) if x]

    haystack = " ".join([title] + dish_types + cuisines + diets + occasions + ingredient_texts)

    if any(str(x).lower() in title for x in rules.get("excludeTitles", []) if x):
        return False
    if any(str(x).lower() in dish_types for x in rules.get("excludeDishTypes", []) if x):
        return False
    if any(str(x).lower() in cuisines for x in rules.get("excludeCuisine", []) if x):
        return False
    if any(str(x).lower() in haystack for x in rules.get("excludeTags", []) if x):
        return False
    if any(str(x).lower() in haystack for x in rules.get("excludeIngredients", []) if x):
        return False

    return True


def _build_spoonacular_params(exclude_data):
    """Build query parameters for Spoonacular complexSearch."""
    rules = exclude_data.get("exclude_rules", {})
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "type": "main course",
        "addRecipeInformation": True,
        "fillIngredients": True,
        "number": 30,
        "instructionsRequired": True,
        "sort": "popularity",
    }
    if rules.get("excludeIngredients"):
        params["excludeIngredients"] = ",".join(rules["excludeIngredients"])
    if rules.get("excludeCuisine"):
        params["excludeCuisine"] = ",".join(rules["excludeCuisine"])
    return params


def _extract_instructions(recipe):
    """Extract human-readable instructions from recipe."""
    # Try analyzedInstructions first
    analyzed = recipe.get("analyzedInstructions", [])
    if analyzed:
        steps = []
        for group in analyzed:
            for step in group.get("steps", []):
                steps.append(f"{step.get('number', '')}. {step.get('step', '')}")
        if steps:
            return "\n".join(steps)
    # Fallback to instructions string
    instructions = recipe.get("instructions", "")
    if instructions:
        # Strip HTML tags
        import re
        clean = re.sub(r"<[^>]+>", "", instructions)
        return clean.strip()
    return ""


def _extract_ingredients(recipe):
    """Extract ingredients list from recipe."""
    ingredients = []
    for ing in recipe.get("extendedIngredients", []):
        original = ing.get("original") or ing.get("originalString") or ""
        if original:
            ingredients.append(original)
    return ingredients


def _translate_recipe(recipe):
    """Translate a Spoonacular recipe to German."""
    translated = dict(recipe)
    # Translate title
    translated["title_en"] = recipe.get("title", "")
    translated["title"] = _translate_text(recipe.get("title", ""))

    # Translate ingredients
    ingredients_en = _extract_ingredients(recipe)
    translated["ingredients_en"] = ingredients_en
    translated["ingredients"] = [_translate_text(i) for i in ingredients_en]

    # Translate instructions
    instructions_en = _extract_instructions(recipe)
    translated["instructions_en"] = instructions_en
    translated["instructions_text"] = _translate_text(instructions_en) if instructions_en else ""

    return translated


def fetch_and_cache_api_recipes(data_dir, cache_dir):
    """Fetch recipes from Spoonacular API and cache them locally.
    Uses a single broad query and applies only exclude-list filtering.
    Returns a result dict:
      - On success: {"success": True, "cached_count": int}
      - On error:   {"success": False, "error_type": str, "message": str,
                      "cached_count": int, "used_fallback": bool}
    """
    exclude_data = load_exclude_list(data_dir)
    exclude_rules = exclude_data.get("exclude_rules", {})
    params = _build_spoonacular_params(exclude_data)
    params["number"] = 100

    all_recipes = []
    seen_ids = set()
    api_error = None

    try:
        logger.info("Fetching Spoonacular recipes with exclude-only logic")
        resp = requests.get(
            f"{SPOONACULAR_BASE}/recipes/complexSearch",
            params=params,
            timeout=15,
        )

        if resp.status_code in (402, 429):
            logger.warning("Spoonacular API quota exceeded (HTTP %s)", resp.status_code)
            api_error = {
                "error_type": "quota_exceeded",
                "message": "Spoonacular API-Kontingent aufgebraucht.",
            }
        elif resp.status_code in (401, 403):
            logger.error("Spoonacular API authentication failed (HTTP %s)", resp.status_code)
            api_error = {
                "error_type": "invalid_key",
                "message": "Ungültiger oder abgelaufener API-Key.",
            }
        elif resp.status_code in (500, 502, 503):
            logger.warning("Spoonacular API unavailable (HTTP %s)", resp.status_code)
            api_error = {
                "error_type": "service_unavailable",
                "message": f"Spoonacular API nicht erreichbar (HTTP {resp.status_code}).",
            }
        elif not resp.ok:
            logger.warning("Spoonacular API returned HTTP %s", resp.status_code)
            api_error = {
                "error_type": "unknown",
                "message": f"API-Fehler (HTTP {resp.status_code}).",
            }
        else:
            data = resp.json()
            for recipe in data.get("results", []):
                rid = recipe.get("id")
                if rid in seen_ids:
                    continue
                if not _recipe_matches_exclude(recipe, exclude_rules):
                    continue
                seen_ids.add(rid)
                recipe["diet_type"] = _classify_diet(recipe)
                recipe = _translate_recipe(recipe)
                recipe["source"] = "api"
                all_recipes.append(recipe)

    except requests.Timeout:
        logger.warning("Spoonacular API request timed out")
        api_error = {
            "error_type": "network_error",
            "message": "Zeitüberschreitung bei der Verbindung zur Spoonacular API.",
        }
    except requests.ConnectionError:
        logger.warning("Could not connect to Spoonacular API")
        api_error = {
            "error_type": "network_error",
            "message": "Keine Verbindung zur Spoonacular API möglich.",
        }
    except requests.RequestException as e:
        logger.warning(f"Spoonacular API request failed: {e}")
        api_error = {
            "error_type": "unknown",
            "message": str(e),
        }

    # Merge with existing cache (keep old recipes if API returned fewer)
    existing = load_cached_recipes(cache_dir)
    existing_ids = {r.get("id") for r in existing if r.get("id")}
    new_ids = {r.get("id") for r in all_recipes if r.get("id")}

    for r in existing:
        if r.get("id") and r["id"] not in new_ids:
            all_recipes.append(r)

    save_cached_recipes(cache_dir, all_recipes)
    logger.info(f"Cached {len(all_recipes)} recipes total")

    # ---------- build result ----------
    if api_error:
        used_fallback = len(existing) > 0
        return {
            "success": False,
            "error_type": api_error["error_type"],
            "message": api_error["message"],
            "cached_count": len(all_recipes),
            "used_fallback": used_fallback,
        }

    return {"success": True, "cached_count": len(all_recipes)}


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def _enrich_fixed_dish(dish):
    """Enrich a fixed dish with diet type and time info."""
    title = dish.get("title", "")
    diets = dish.get("diets", ["vegetarian"])
    diet_type = diets[0] if diets else "vegetarian"
    return {
        "id": f"fixed_{title.lower().replace(' ', '_')}",
        "title": title,
        "image": dish.get("image", ""),
        "readyInMinutes": dish.get("readyInMinutes", 30),
        "diet_type": diet_type,
        "source": "fixed",
        "servings": dish.get("servings", 4),
        "ingredients": [],
        "instructions_text": "",
        "extendedIngredients": dish.get("extendedIngredients", []),
        "analyzedInstructions": dish.get("analyzedInstructions", []),
    }


def _make_free_card(description=""):
    """Create a free card entry."""
    return {
        "id": f"free_{random.randint(10000,99999)}",
        "title": "Freie Karte",
        "image": "",
        "readyInMinutes": 0,
        "diet_type": "free",
        "source": "free",
        "servings": 0,
        "ingredients": [],
        "instructions_text": "",
        "description": description,
    }


def generate_weekly_plan(data_dir, cache_dir, free_days=None, week_offset=0, include_api_recipes=True):
    """
    Generate a 7-day lunch plan (Monday-Sunday).

    Uses fixed diet distribution and filters only by exclude-list rules.
    Weekdays (Mon-Fri): max 45 min prep time
    Weekends (Sat-Sun): no time restriction
    No duplicates within the week.
    """
    if free_days is None:
        free_days = []

    exclude_data = load_exclude_list(data_dir)
    exclude_rules = exclude_data.get("exclude_rules", {})

    fixed_dishes = load_fixed_dishes(data_dir)
    fixed_enriched = [_enrich_fixed_dish(d) for d in fixed_dishes]
    cached_recipes = load_cached_recipes(cache_dir) if include_api_recipes else []

    combined_pool = []
    for dish in fixed_enriched:
        if _recipe_matches_exclude(dish, exclude_rules):
            combined_pool.append(dish)
    for recipe in cached_recipes:
        if _recipe_matches_exclude(recipe, exclude_rules):
            combined_pool.append(recipe)

    fixed_distribution = ["vegan", "vegetarian", "vegetarian", "vegetarian", "meat", "meat", "fish"]
    non_free_days = [idx for idx in range(7) if idx not in free_days]
    random.shuffle(fixed_distribution)
    assigned_diets = {day_idx: fixed_distribution[i] for i, day_idx in enumerate(non_free_days[:len(fixed_distribution)])}

    pool_by_diet = {"vegan": [], "vegetarian": [], "meat": [], "fish": []}
    for recipe in combined_pool:
        diet_type = recipe.get("diet_type")
        if diet_type in pool_by_diet:
            pool_by_diet[diet_type].append(recipe)

    for diet_type in pool_by_diet:
        random.shuffle(pool_by_diet[diet_type])

    used_titles = set()
    plan = []
    dates = get_current_week_dates(week_offset)

    for day_idx in range(7):
        day_info = dates["days"][day_idx]
        is_weekend = day_info["is_weekend"]

        if day_idx in free_days:
            entry = _make_free_card()
            entry["day_name"] = day_info["name"]
            entry["day_index"] = day_idx
            entry["date"] = day_info["date"]
            plan.append(entry)
            continue

        target_diet = assigned_diets.get(day_idx)
        selected = None

        for recipe in pool_by_diet.get(target_diet, []):
            title = recipe.get("title", "")
            if not title or title in used_titles:
                continue
            prep_time = recipe.get("readyInMinutes", 0)
            if not is_weekend and prep_time > WEEKDAY_MAX_MINUTES and prep_time > 0:
                continue
            selected = recipe
            break

        if selected is None:
            for recipe in pool_by_diet.get(target_diet, []):
                title = recipe.get("title", "")
                if not title or title in used_titles:
                    continue
                selected = recipe
                break

        if selected is None:
            selected = _make_free_card(f"Kein passendes {target_diet}-Gericht gefunden")
            selected["diet_type"] = target_diet

        used_titles.add(selected.get("title", ""))
        entry = dict(selected)
        entry["day_name"] = day_info["name"]
        entry["day_index"] = day_idx
        entry["date"] = day_info["date"]
        plan.append(entry)

    return plan


def get_swap_candidates(data_dir, cache_dir, current_titles, swap_type="all"):
    """Get replacement candidates for swapping a day's meal.
    Excludes dishes already in the current week plan."""
    current_set = set(current_titles)
    candidates = []

    if swap_type in ("fixed", "all"):
        fixed_dishes = load_fixed_dishes(data_dir)
        for d in fixed_dishes:
            enriched = _enrich_fixed_dish(d)
            if enriched["title"] not in current_set:
                candidates.append(enriched)

    if swap_type in ("api", "all"):
        cached = load_cached_recipes(cache_dir)
        for r in cached:
            if r.get("title", "") not in current_set:
                candidates.append(r)

    return candidates

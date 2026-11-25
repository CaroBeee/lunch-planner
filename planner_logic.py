"""
Core planning logic for the 7-Day Lunch Planner.
Handles plan generation and fixed-dish selection.
"""

import os
import json
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
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


def generate_weekly_plan(data_dir, free_days=None, week_offset=0):
    """
    Generate a 7-day lunch plan (Monday-Sunday) from fixed dishes.

    Weekdays (Mon-Fri): max 45 min prep time
    Weekends: no time restriction
    No duplicates within the week.
    """
    if free_days is None:
        free_days = []

    fixed_dishes = load_fixed_dishes(data_dir)
    fixed_enriched = [_enrich_fixed_dish(dish) for dish in fixed_dishes]

    fixed_distribution = ["vegan", "vegetarian", "vegetarian", "vegetarian", "meat", "meat", "fish"]
    non_free_days = [idx for idx in range(7) if idx not in free_days]
    random.shuffle(fixed_distribution)
    assigned_diets = {
        day_idx: fixed_distribution[i]
        for i, day_idx in enumerate(non_free_days[:len(fixed_distribution)])
    }

    pool_by_diet = {"vegan": [], "vegetarian": [], "meat": [], "fish": []}
    for dish in fixed_enriched:
        diet_type = dish.get("diet_type")
        if diet_type in pool_by_diet:
            pool_by_diet[diet_type].append(dish)

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

        for dish in pool_by_diet.get(target_diet, []):
            title = dish.get("title", "")
            if not title or title in used_titles:
                continue
            prep_time = dish.get("readyInMinutes", 0)
            if not is_weekend and prep_time > WEEKDAY_MAX_MINUTES and prep_time > 0:
                continue
            selected = dish
            break

        if selected is None:
            for dish in pool_by_diet.get(target_diet, []):
                title = dish.get("title", "")
                if not title or title in used_titles:
                    continue
                selected = dish
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


def get_swap_candidates(data_dir, current_titles):
    """Return fixed dishes that are not already used in the current plan."""
    current_set = set(current_titles)
    candidates = []

    for dish in load_fixed_dishes(data_dir):
        enriched = _enrich_fixed_dish(dish)
        if enriched["title"] not in current_set:
            candidates.append(enriched)

    return candidates

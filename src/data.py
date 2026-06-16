from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from src.supabase_client import get_supabase


def _rows(response: Any) -> list[dict[str, Any]]:
    return list(response.data or [])


def _format_quantity(value: Any) -> str:
    if value is None:
        return ""
    try:
        number = Decimal(str(value)).normalize()
        return format(number, "f")
    except Exception:
        return str(value)


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def list_recipes() -> list[dict[str, Any]]:
    supabase = get_supabase()
    recipes = _rows(
        supabase.table("recipes")
        .select(
            "id,title,description,servings,prep_time_min,cook_time_min,total_time_min,instructions,created_at"
        )
        .order("created_at", desc=True)
        .execute()
    )

    if not recipes:
        return []

    recipe_ids = [recipe["id"] for recipe in recipes]
    ingredient_rows = _rows(
        supabase.table("recipe_ingredients")
        .select("recipe_id,ingredient_id,quantity,unit,comment,ingredients(name,default_unit)")
        .in_("recipe_id", recipe_ids)
        .execute()
    )

    by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ingredient_rows:
        ingredient = row.get("ingredients") or {}
        quantity = _format_quantity(row.get("quantity"))
        unit = row.get("unit") or ingredient.get("default_unit") or ""
        pieces = [piece for piece in [quantity, unit, ingredient.get("name")] if piece]
        by_recipe[row["recipe_id"]].append(
            {
                "ingredient_id": row.get("ingredient_id"),
                "name": ingredient.get("name") or "Ingredient",
                "quantity": row.get("quantity"),
                "unit": unit,
                "text": " ".join(pieces),
                "comment": row.get("comment") or "",
            }
        )

    for recipe in recipes:
        recipe["ingredients"] = by_recipe.get(recipe["id"], [])

    return recipes


def list_ingredients() -> list[dict[str, Any]]:
    supabase = get_supabase()
    return _rows(
        supabase.table("ingredients")
        .select("id,name,default_unit")
        .order("name")
        .execute()
    )


def find_user_by_email(email: str) -> dict[str, Any] | None:
    supabase = get_supabase()
    normalized_email = email.strip()
    existing = _rows(
        supabase.table("app_users")
        .select("id,name,email")
        .ilike("email", normalized_email)
        .limit(1)
        .execute()
    )
    if existing:
        return existing[0]
    return None


def list_fridge_items(user_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return _rows(
        supabase.table("user_fridge_ingredients")
        .select("id,quantity,unit,expires_at,ingredients(id,name,default_unit)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )


def add_fridge_item(
    user_id: str,
    ingredient_id: str,
    quantity: float | None,
    unit: str | None,
    expires_at: str | None,
) -> None:
    supabase = get_supabase()
    supabase.table("user_fridge_ingredients").insert(
        {
            "user_id": user_id,
            "ingredient_id": ingredient_id,
            "quantity": quantity,
            "unit": unit or None,
            "expires_at": expires_at or None,
        }
    ).execute()


def delete_fridge_item(row_id: str) -> None:
    get_supabase().table("user_fridge_ingredients").delete().eq("id", row_id).execute()


def list_saved_recipe_ids(user_id: str) -> set[str]:
    supabase = get_supabase()
    rows = _rows(
        supabase.table("user_recipes")
        .select("recipe_id")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["recipe_id"] for row in rows}


def save_recipe(user_id: str, recipe_id: str) -> None:
    supabase = get_supabase()
    supabase.table("user_recipes").upsert(
        {"user_id": user_id, "recipe_id": recipe_id},
        on_conflict="user_id,recipe_id",
    ).execute()


def unsave_recipe(user_id: str, recipe_id: str) -> None:
    get_supabase().table("user_recipes").delete().eq("user_id", user_id).eq(
        "recipe_id", recipe_id
    ).execute()


def match_recipes_by_fridge(
    recipes: list[dict[str, Any]], fridge_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    fridge_names = {
        (item.get("ingredients") or {}).get("name", "").strip().lower()
        for item in fridge_items
    }
    fridge_names.discard("")

    matched = []
    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])
        required = {
            ingredient.get("name", "").strip().lower()
            for ingredient in ingredients
            if ingredient.get("name")
        }
        if not required:
            score = 0
            missing = []
        else:
            score = round(len(required & fridge_names) / len(required) * 100)
            missing = sorted(required - fridge_names)

        recipe_copy = dict(recipe)
        recipe_copy["match_score"] = score
        recipe_copy["missing_ingredients"] = missing
        matched.append(recipe_copy)

    return sorted(matched, key=lambda item: item["match_score"], reverse=True)


def build_shopping_list(
    saved_recipes: list[dict[str, Any]], fridge_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    needed: dict[tuple[str, str], dict[str, Any]] = {}
    fridge: dict[tuple[str, str], Decimal] = defaultdict(Decimal)

    for item in fridge_items:
        ingredient = item.get("ingredients") or {}
        ingredient_id = ingredient.get("id")
        unit = item.get("unit") or ingredient.get("default_unit") or ""
        quantity = _to_decimal(item.get("quantity"))
        if ingredient_id and quantity is not None:
            fridge[(ingredient_id, unit)] += quantity

    for recipe in saved_recipes:
        for ingredient in recipe.get("ingredients", []):
            ingredient_id = ingredient.get("ingredient_id")
            unit = ingredient.get("unit") or ""
            if not ingredient_id:
                continue

            key = (ingredient_id, unit)
            quantity = _to_decimal(ingredient.get("quantity"))
            if key not in needed:
                needed[key] = {
                    "ingredient_id": ingredient_id,
                    "name": ingredient.get("name") or "Ingredient",
                    "unit": unit,
                    "quantity": Decimal(0),
                    "without_quantity": False,
                    "recipes": set(),
                }

            if quantity is None:
                needed[key]["without_quantity"] = True
            else:
                needed[key]["quantity"] += quantity
            needed[key]["recipes"].add(recipe["title"])

    shopping_items = []
    for key, item in needed.items():
        remaining = item["quantity"] - fridge.get(key, Decimal(0))
        if remaining <= 0 and not item["without_quantity"]:
            continue

        shopping_items.append(
            {
                "name": item["name"],
                "quantity": None if item["without_quantity"] else _format_quantity(remaining),
                "unit": item["unit"],
                "recipes": sorted(item["recipes"]),
            }
        )

    return sorted(shopping_items, key=lambda item: item["name"].lower())

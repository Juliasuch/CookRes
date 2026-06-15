from __future__ import annotations

import streamlit as st

from src.data import (
    add_fridge_item,
    build_shopping_list,
    delete_fridge_item,
    get_or_create_user,
    list_fridge_items,
    list_ingredients,
    list_recipes,
    list_saved_recipe_ids,
    save_recipe,
    unsave_recipe,
)
from src.ui import render_recipe_card


st.set_page_config(
    page_title="CookRes",
    page_icon="🍳",
    layout="wide",
)


def require_user() -> dict[str, str] | None:
    with st.sidebar:
        st.title("CookRes")
        st.caption("Выбери рецепты, проверь холодильник и собери список покупок.")

        email = st.text_input("Email", placeholder="you@example.com")
        name = st.text_input("Имя", placeholder="Юлия")

        if not email:
            st.info("Введите email, чтобы открыть свои рецепты, холодильник и список покупок.")
            return None

        try:
            user = get_or_create_user(email=email, name=name)
        except Exception as error:
            st.error("Не получилось подключиться к Supabase.")
            st.caption(str(error))
            return None

        st.success(f"Профиль: {user.get('name') or user['email']}")
        return user


def handle_save_action(action: str | None, user_id: str, recipe_id: str) -> None:
    if action == "save":
        save_recipe(user_id, recipe_id)
        st.toast("Рецепт сохранен")
        st.rerun()
    if action == "unsave":
        unsave_recipe(user_id, recipe_id)
        st.toast("Рецепт убран из сохраненных")
        st.rerun()


def render_recipe_list(
    recipes: list[dict],
    user_id: str,
    saved_ids: set[str],
    key_prefix: str,
    *,
    save_label: str = "Выбрать",
    unsave_label: str = "Убрать",
) -> None:
    if not recipes:
        st.info("Пока здесь нет рецептов.")
        return

    for recipe in recipes:
        action = render_recipe_card(
            recipe,
            saved=recipe["id"] in saved_ids,
            on_save_key=f"{key_prefix}-save-{recipe['id']}",
            on_unsave_key=f"{key_prefix}-unsave-{recipe['id']}",
            save_label=save_label,
            unsave_label=unsave_label,
        )
        handle_save_action(action, user_id, recipe["id"])


def render_fridge_tab(user_id: str) -> None:
    st.header("Мой холодильник")

    ingredients = list_ingredients()
    ingredient_options = {
        f"{item['name']} ({item.get('default_unit') or 'без ед.'})": item for item in ingredients
    }

    if not ingredient_options:
        st.info("Сначала добавьте ингредиенты в таблицу ingredients в Supabase.")
        return

    with st.form("add-fridge-item", border=True):
        cols = st.columns([0.42, 0.18, 0.18, 0.22])
        selected_label = cols[0].selectbox("Ингредиент", list(ingredient_options.keys()))
        quantity = cols[1].number_input("Количество", min_value=0.0, step=0.5)
        unit = cols[2].text_input("Ед.", value=ingredient_options[selected_label].get("default_unit") or "")
        expires_at = cols[3].date_input("Годен до", value=None)
        submitted = st.form_submit_button("Добавить", use_container_width=True)

    if submitted:
        add_fridge_item(
            user_id=user_id,
            ingredient_id=ingredient_options[selected_label]["id"],
            quantity=quantity if quantity else None,
            unit=unit,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        st.toast("Добавлено в холодильник")
        st.rerun()

    items = list_fridge_items(user_id)
    if not items:
        st.info("Добавьте продукты, и список покупок будет автоматически уменьшаться.")
        return

    for item in items:
        ingredient = item.get("ingredients") or {}
        cols = st.columns([0.5, 0.2, 0.2, 0.1], vertical_alignment="center")
        cols[0].write(ingredient.get("name", "Ингредиент"))
        cols[1].write(f"{item.get('quantity') or ''} {item.get('unit') or ingredient.get('default_unit') or ''}")
        cols[2].write(item.get("expires_at") or "")
        if cols[3].button("Удалить", key=f"delete-fridge-{item['id']}"):
            delete_fridge_item(item["id"])
            st.rerun()


def render_shopping_list(saved_recipes: list[dict], fridge_items: list[dict]) -> None:
    st.header("Мой список покупок")

    if not saved_recipes:
        st.info("Выберите рецепты во вкладке «Все рецепты», и здесь появятся нужные продукты.")
        return

    shopping_items = build_shopping_list(saved_recipes, fridge_items)
    if not shopping_items:
        st.success("Похоже, для выбранных рецептов все уже есть в холодильнике.")
        return

    for index, item in enumerate(shopping_items):
        amount = " ".join(
            piece for piece in [item.get("quantity"), item.get("unit")] if piece
        )
        label = item["name"] if not amount else f"{item['name']} — {amount}"
        checked = st.checkbox(label, key=f"shopping-done-{index}-{item['name']}")
        if item.get("recipes"):
            st.caption("Для: " + ", ".join(item["recipes"]))
        if checked:
            st.divider()


def main() -> None:
    user = require_user()
    if not user:
        return

    try:
        recipes = list_recipes()
        saved_ids = list_saved_recipe_ids(user["id"])
    except Exception as error:
        st.error("Не получилось загрузить данные из Supabase.")
        st.caption(str(error))
        return

    all_tab, my_recipes_tab, fridge_tab, shopping_tab = st.tabs(
        ["Все рецепты", "Мои рецепты", "Мой холодильник", "Мой список покупок"]
    )

    with all_tab:
        st.header("Все рецепты")
        st.caption("Выберите рецепт, чтобы добавить его в «Мои рецепты».")
        query = st.text_input("Поиск", placeholder="Паста, курица, суп...", key="recipe-search")
        filtered = [
            recipe
            for recipe in recipes
            if not query or query.lower() in recipe["title"].lower()
        ]
        render_recipe_list(
            filtered,
            user["id"],
            saved_ids,
            "all",
            save_label="Выбрать",
            unsave_label="В моих",
        )

    saved_recipes = [recipe for recipe in recipes if recipe["id"] in saved_ids]

    with my_recipes_tab:
        st.header("Мои рецепты")
        st.caption("Здесь собраны выбранные рецепты. Их ингредиенты попадут в список покупок.")
        render_recipe_list(
            saved_recipes,
            user["id"],
            saved_ids,
            "mine",
            save_label="Выбрать",
            unsave_label="Убрать",
        )

    with fridge_tab:
        render_fridge_tab(user["id"])

    with shopping_tab:
        fridge_items = list_fridge_items(user["id"])
        render_shopping_list(saved_recipes, fridge_items)


if __name__ == "__main__":
    main()

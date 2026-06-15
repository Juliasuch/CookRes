from __future__ import annotations

from typing import Any

import streamlit as st


def render_recipe_card(
    recipe: dict[str, Any],
    *,
    saved: bool,
    on_save_key: str,
    on_unsave_key: str,
    save_label: str = "Добавить",
    unsave_label: str = "Убрать",
) -> str | None:
    with st.container(border=True):
        top = st.columns([0.72, 0.28], vertical_alignment="center")
        with top[0]:
            st.subheader(recipe["title"])
            if recipe.get("description"):
                st.caption(recipe["description"])
        with top[1]:
            action_label = unsave_label if saved else save_label
            action_key = on_unsave_key if saved else on_save_key
            if st.button(action_label, key=action_key, use_container_width=True):
                return "unsave" if saved else "save"

        facts = []
        if recipe.get("servings"):
            facts.append(f"{recipe['servings']} порц.")
        if recipe.get("total_time_min"):
            facts.append(f"{recipe['total_time_min']} мин")
        elif recipe.get("prep_time_min") or recipe.get("cook_time_min"):
            total = (recipe.get("prep_time_min") or 0) + (recipe.get("cook_time_min") or 0)
            facts.append(f"{total} мин")
        if facts:
            st.write(" · ".join(facts))

        if "match_score" in recipe:
            st.progress(recipe["match_score"] / 100, text=f"Совпадение: {recipe['match_score']}%")
            if recipe.get("missing_ingredients"):
                st.caption("Не хватает: " + ", ".join(recipe["missing_ingredients"]))

        ingredients = recipe.get("ingredients") or []
        if ingredients:
            with st.expander("Ингредиенты", expanded=False):
                for ingredient in ingredients:
                    line = ingredient["text"]
                    if ingredient.get("comment"):
                        line = f"{line} ({ingredient['comment']})"
                    st.write(f"- {line}")

        if recipe.get("instructions"):
            with st.expander("Как готовить", expanded=False):
                st.write(recipe["instructions"])

    return None

# CookRes

Streamlit-приложение для рецептов на Supabase.

## Что уже заложено

- 4 вкладки: все рецепты, мои рецепты, мой холодильник, мой список покупок.
- Подключение к Supabase через `SUPABASE_URL` и `SUPABASE_PUBLISHABLE_KEY`.
- Работа с текущими таблицами: `recipes`, `ingredients`, `recipe_ingredients`, `app_users`, `user_fridge_ingredients`, `user_recipes`.
- Автоматический список покупок: ингредиенты из выбранных рецептов минус продукты в холодильнике.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

В `.streamlit/secrets.toml` нужно указать URL проекта Supabase и anon/publishable key.

## Рекомендуемые правила доступа в Supabase

Для первого read-only прототипа можно открыть чтение справочников и рецептов через RLS:

```sql
alter table recipes enable row level security;
alter table ingredients enable row level security;
alter table recipe_ingredients enable row level security;

create policy "Public recipes are readable"
on recipes for select
to anon, authenticated
using (true);

create policy "Ingredients are readable"
on ingredients for select
to anon, authenticated
using (true);

create policy "Recipe ingredients are readable"
on recipe_ingredients for select
to anon, authenticated
using (true);
```

Сейчас приложение использует прототипный режим без пароля: пользователь вводит email, приложение ищет его в `app_users`, а затем использует `app_users.id` как `user_id`. Поэтому для Supabase такие запросы идут от роли `anon`, а не от `authenticated`, и policies через `auth.uid()` работать не будут.

Для такого учебного прототипа можно использовать более открытые policies:

```sql
alter table app_users enable row level security;
alter table user_recipes enable row level security;
alter table user_fridge_ingredients enable row level security;

create policy "Prototype users are readable"
on app_users for select
to anon, authenticated
using (true);

create policy "Prototype selected recipes are readable"
on user_recipes for select
to anon, authenticated
using (true);

create policy "Prototype selected recipes are writable"
on user_recipes for insert
to anon, authenticated
with check (
  exists (
    select 1
    from app_users
    where app_users.id = user_recipes.user_id
  )
);

create policy "Prototype selected recipes are removable"
on user_recipes for delete
to anon, authenticated
using (true);

create policy "Prototype fridge is readable"
on user_fridge_ingredients for select
to anon, authenticated
using (true);

create policy "Prototype fridge is writable"
on user_fridge_ingredients for insert
to anon, authenticated
with check (
  exists (
    select 1
    from app_users
    where app_users.id = user_fridge_ingredients.user_id
  )
);

create policy "Prototype fridge is removable"
on user_fridge_ingredients for delete
to anon, authenticated
using (true);
```

Это удобно для демо и учебного проекта, но не является приватной авторизацией: любой человек, знающий email, сможет открыть данные этого профиля. Для публичной версии лучше перейти на Supabase Auth или magic link.

## Логика вкладок

1. `Все рецепты`: показывает все рецепты из таблицы `recipes`; кнопка `Выбрать` добавляет рецепт в `user_recipes`.
2. `Мои рецепты`: показывает выбранные рецепты; кнопка `Убрать` удаляет рецепт из `user_recipes`.
3. `Мой холодильник`: позволяет выбрать ингредиент из `ingredients`, указать количество и сохранить его в `user_fridge_ingredients`.
4. `Мой список покупок`: суммирует ингредиенты из выбранных рецептов и вычитает продукты из холодильника. Галочки сейчас хранятся только на экране Streamlit; если нужно сохранять их между сессиями, понадобится отдельная таблица.

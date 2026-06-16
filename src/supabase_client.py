from __future__ import annotations

import streamlit as st
from supabase import Client, create_client

from src.config import get_any_secret, get_secret


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    return create_client(
        get_secret("SUPABASE_URL"),
        get_any_secret("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
    )

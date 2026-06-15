from __future__ import annotations

import os

import streamlit as st


def get_secret(name: str) -> str:
    value = st.secrets.get(name) or os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return str(value)

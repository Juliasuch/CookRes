from __future__ import annotations

import os

import streamlit as st


def get_secret(name: str) -> str:
    value = st.secrets.get(name) or os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return str(value)


def get_any_secret(*names: str) -> str:
    for name in names:
        value = st.secrets.get(name) or os.getenv(name)
        if value:
            return str(value)
    raise RuntimeError(f"Missing required setting: {' or '.join(names)}")

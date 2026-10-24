"""Small helpers shared by every screen."""
import datetime as dt

import streamlit as st


def flash(message, kind="success"):
    """Show a message AFTER the next rerun (st.rerun() would erase a normal st.success)."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def nonce(name):
    """A counter used inside widget keys. Bump it to get brand-new, EMPTY form fields."""
    return st.session_state.get(name, 0)


def bump(name):
    st.session_state[name] = nonce(name) + 1


def to_date(text):
    """'2024-08-15' -> date (or None for blanks)."""
    return dt.date.fromisoformat(text) if text else None

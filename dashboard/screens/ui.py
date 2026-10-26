"""Small helpers shared by every screen: messages, looks, table formats."""
import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BRAND = "#2F6FDE"
LOGO = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


# ------------------------------------------------------------------ messages
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


# --------------------------------------------------------------------- looks
def inject_css():
    """A few small touches the theme file cannot do."""
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1280px;}
        h1, h2, h3 {letter-spacing: -0.01em;}
        [data-testid="stSidebar"] [data-testid="stImage"] {margin-bottom: 0.4rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle=None):
    st.header(title)
    if subtitle:
        st.caption(subtitle)


def card():
    """A bordered box. Use as:  with ui.card(): ..."""
    return st.container(border=True)


def table_height(rows, maximum=520):
    """Short tables fit their rows exactly; long ones get a fixed height and scroll."""
    return "content" if rows <= 13 else maximum


def bar_chart(df, category, value, color=BRAND, whole_numbers=False, number_format=",d"):
    """Horizontal bars, biggest on top, full labels, tooltip on hover."""
    height = 60 + 44 * len(df)
    axis = alt.Axis(tickMinStep=1, format="d") if whole_numbers else alt.Axis(format=number_format)
    chart = (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadiusEnd=4)
        .encode(
            x=alt.X(f"{value}:Q", title=None, axis=axis),
            y=alt.Y(f"{category}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
            tooltip=[alt.Tooltip(f"{category}:N", title="Department"),
                     alt.Tooltip(f"{value}:Q", title=value.replace("_", " ").capitalize(), format=",d")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, width="stretch")


# --------------------------------------------------------------- table looks
def money(label):
    return st.column_config.NumberColumn(label, format="localized")


def day(label):
    return st.column_config.DateColumn(label, format="DD MMM YYYY")


def to_days(df, *columns):
    """Turn text columns like '2024-08-15' into real dates so they can be formatted."""
    df = df.copy()
    for column in columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df

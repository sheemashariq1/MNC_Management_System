import pandas as pd
import streamlit as st

import api_client
from screens import ui


def show():
    ui.page_header("Building overview", "Live headcount of every floor of the SKILLWAY building.")
    ui.show_flash()
    rows = api_client.overview()
    df = pd.DataFrame(rows, columns=["floor", "department", "employees"])
    total = int(df["employees"].sum())
    busiest = df.loc[df["employees"].idxmax(), "department"] if total else "-"

    c1, c2, c3 = st.columns(3)
    with c1, ui.card():
        st.metric("Employees", total)
    with c2, ui.card():
        st.metric("Departments", len(df))
    with c3, ui.card():
        st.metric("Busiest department", busiest)

    left, right = st.columns([2, 3])
    with left, ui.card():
        st.subheader("Floors")
        st.dataframe(df, hide_index=True, width="stretch", height=ui.table_height(len(df)),
                     column_config={"floor": st.column_config.NumberColumn("Floor", format="%d"),
                                    "department": "Department",
                                    "employees": st.column_config.NumberColumn("Employees", format="%d")})
    with right, ui.card():
        st.subheader("Employees per department")
        if total:
            ui.bar_chart(df, "department", "employees", whole_numbers=True)
        else:
            st.info("No employees yet. Hire the first one on the Employees page.")

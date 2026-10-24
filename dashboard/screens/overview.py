import pandas as pd
import streamlit as st

import api_client
from screens import ui


def show():
    st.header("Building overview")
    ui.show_flash()
    rows = api_client.overview()
    df = pd.DataFrame(rows, columns=["floor", "department", "employees"])
    total = int(df["employees"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Employees", total)
    c2.metric("Departments", len(df))
    busiest = df.loc[df["employees"].idxmax(), "department"] if total else "-"
    c3.metric("Busiest department", busiest)

    left, right = st.columns([3, 2])
    left.dataframe(df.rename(columns={"floor": "Floor", "department": "Department",
                                      "employees": "Employees"}),
                   hide_index=True, width="stretch")
    right.bar_chart(df.set_index("department")["employees"])

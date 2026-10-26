import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui


def show():
    ui.page_header("Reports", "Salary and headcount per department, with downloads.")
    ui.show_flash()
    rows = api_client.report_summary()
    if not rows:
        st.info("There are no employees yet, so there is nothing to report.")
        return
    df = pd.DataFrame(rows)

    with ui.card():
        st.subheader("Department-wise summary")
        st.dataframe(df, hide_index=True, width="stretch", height=ui.table_height(len(df)),
                     column_config={
                         "Employees": st.column_config.NumberColumn("Employees", format="%d"),
                         "Total salary": ui.money("Total salary"),
                         "Average salary": ui.money("Average salary"),
                         "Median salary": ui.money("Median salary"),
                         "Highest salary": ui.money("Highest salary"),
                         "Avg years of service": st.column_config.NumberColumn(
                             "Avg years of service", format="%.1f")})

    left, right = st.columns(2)
    with left, ui.card():
        st.subheader("Employees per department")
        ui.bar_chart(df, "Department", "Employees", whole_numbers=True)
    with right, ui.card():
        st.subheader("Average salary per department")
        paid = df[df["Average salary"] > 0]
        if paid.empty:
            st.info("No salaries yet.")
        else:
            ui.bar_chart(paid, "Department", "Average salary", color="#1E8E3E")

    with ui.card():
        st.subheader("Download")
        st.caption("Preparing a report creates the file on the server and is written to the audit log.")
        c1, c2 = st.columns(2)
        for column, label, key, loader, mime in (
                (c1, "Prepare Excel report", "report_excel", api_client.export_excel,
                 api_client.EXCEL_TYPE),
                (c2, "Prepare CSV (employees)", "report_csv", api_client.export_csv, "text/csv")):
            if column.button(label, key=key + "_prepare"):
                try:
                    st.session_state[key] = loader()
                except ApiError as err:
                    column.error(err.message)
            if key in st.session_state:
                data, name = st.session_state[key]
                column.download_button(f"Download {name}", data=data, file_name=name, mime=mime,
                                       key=key + "_download", type="primary")

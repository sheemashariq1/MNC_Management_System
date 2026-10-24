import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui


def show():
    st.header("Reports")
    ui.show_flash()
    rows = api_client.report_summary()
    if not rows:
        st.info("There are no employees yet, so there is nothing to report.")
        return
    df = pd.DataFrame(rows)
    st.subheader("Department-wise summary")
    st.dataframe(df, hide_index=True, width="stretch")

    left, right = st.columns(2)
    left.subheader("Employees per department")
    left.bar_chart(df.set_index("Department")["Employees"])
    paid = df[df["Average salary"] > 0]
    right.subheader("Average salary per department")
    if paid.empty:
        right.info("No salaries yet.")
    else:
        right.bar_chart(paid.set_index("Department")["Average salary"])

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
                                   key=key + "_download")

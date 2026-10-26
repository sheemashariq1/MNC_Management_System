import pandas as pd
import streamlit as st

import api_client
from screens import ui


def show():
    ui.page_header("Audit log", "Who did what, and when. Newest first.")
    ui.show_flash()
    a, b, c = st.columns([2, 2, 1])
    username = a.text_input("Only this username", key="audit_user")
    action = b.text_input("Action contains (e.g. EMP_, LOGIN)", key="audit_action")
    limit = c.number_input("How many", min_value=1, max_value=500, value=50, step=10,
                           key="audit_limit")
    rows = api_client.audit(int(limit), username.strip() or None, action.strip() or None)
    if rows:
        df = ui.to_days(pd.DataFrame(rows, columns=["id", "when", "username", "role", "action", "details"]),
                        "when")
        st.dataframe(df, hide_index=True, width="stretch", height=ui.table_height(len(df), 640),
                     column_config={"id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                                    "when": st.column_config.DatetimeColumn("When", format="DD MMM YYYY, HH:mm:ss"),
                                    "username": "User", "role": "Role", "action": "Action",
                                    "details": st.column_config.TextColumn("Details", width="large")})
    else:
        st.info("No entries match.")

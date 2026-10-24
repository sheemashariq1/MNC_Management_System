import pandas as pd
import streamlit as st

import api_client
from screens import ui


def show():
    st.header("Audit log")
    st.caption("Who did what, and when. Newest first.")
    ui.show_flash()
    a, b, c = st.columns([2, 2, 1])
    username = a.text_input("Only this username", key="audit_user")
    action = b.text_input("Action contains (e.g. EMP_, LOGIN)", key="audit_action")
    limit = c.number_input("How many", min_value=1, max_value=500, value=50, step=10,
                           key="audit_limit")
    rows = api_client.audit(int(limit), username.strip() or None, action.strip() or None)
    if rows:
        st.dataframe(pd.DataFrame(rows, columns=["id", "when", "username", "role", "action", "details"]),
                     hide_index=True, width="stretch")
    else:
        st.info("No entries match.")

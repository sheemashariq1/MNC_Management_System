import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui

ROLES = ["admin", "hr", "it"]


def show():
    st.header("User accounts")
    ui.show_flash()
    rows = api_client.users()
    st.dataframe(pd.DataFrame(rows, columns=["username", "role"]), hide_index=True, width="stretch")
    names = [r["username"] for r in rows]
    me = st.session_state["username"]

    role_tab, delete_tab = st.tabs(["Change role", "Delete account"])
    with role_tab:
        with st.form("role_form"):
            who = st.selectbox("User", names, key="role_user")
            role = st.selectbox("New role", ROLES, key="role_new")
            submitted = st.form_submit_button("Change role", key="role_submit")
        if submitted:
            try:
                api_client.change_role(who, role)
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"{who} is now {role}.")
                st.rerun()

    with delete_tab:
        who = st.selectbox("Account to delete", names, key="del_user")
        st.warning(f"You are signed in as {me}. You cannot delete yourself.")
        sure = st.checkbox("I am sure", key="del_user_sure")
        if st.button("Delete account", disabled=not sure, key="del_user_go"):
            try:
                api_client.delete_user(who)
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"Account {who} deleted.")
                st.rerun()

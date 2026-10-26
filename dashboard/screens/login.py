"""The page people see before they are logged in."""
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui


def _start_session(data):
    st.session_state["token"] = data["access_token"]
    st.session_state["username"] = data["username"]
    st.session_state["role"] = data["role"]
    st.rerun()


def show():
    _, middle, _ = st.columns([1, 1.9, 1])          # a narrow, centred card instead of a stretched form
    with middle:
        st.image(str(ui.LOGO), width=300)
        st.title("MNC Management System")
        st.caption("Employees, departments and reports of the SKILLWAY IT Company, Gurgaon.")
        ui.show_flash()
        sign_in, sign_up = st.tabs(["Sign in", "Create account"])

        with sign_in:
            with st.form("login_form", border=False):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign in", key="login_submit", type="primary",
                                                  width="stretch")
            if submitted:
                try:
                    _start_session(api_client.login(username.strip(), password))
                except ApiError as err:
                    st.error(err.message)

        with sign_up:
            st.caption("Ask the company for your access code. It decides your role.")
            with st.form("register_form", border=False):
                username = st.text_input("Choose a username (3-20 characters)", key="reg_username")
                password = st.text_input("Password (min 6 characters)", type="password", key="reg_password")
                confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
                code = st.text_input("Access code", type="password", key="reg_code")
                submitted = st.form_submit_button("Create account", key="reg_submit", type="primary",
                                                  width="stretch")
            if submitted:
                if password != confirm:
                    st.error("The two passwords do not match.")
                else:
                    try:
                        _start_session(api_client.register(username.strip(), password, code))
                    except ApiError as err:
                        st.error(err.message)

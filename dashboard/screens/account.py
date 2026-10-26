import streamlit as st

import api_client
from api_client import ApiError
from screens import ui


def show():
    ui.page_header("My account", "Your sign-in details and password.")
    ui.show_flash()
    with ui.card():
        st.write(f"Username: **{st.session_state['username']}**")
        st.markdown(f"Role: :blue-badge[{st.session_state['role']}]")

    st.subheader("Change password")
    with st.form("password_form"):
        current = st.text_input("Current password", type="password", key="pw_current")
        new = st.text_input("New password (min 6 characters)", type="password", key="pw_new")
        confirm = st.text_input("Confirm new password", type="password", key="pw_confirm")
        submitted = st.form_submit_button("Change password", key="pw_submit")
    if submitted:
        if new != confirm:
            st.error("The two new passwords do not match.")
        else:
            try:
                api_client.change_password(current, new)
            except ApiError as err:
                st.error(err.message)
            else:
                st.success("Password changed.")

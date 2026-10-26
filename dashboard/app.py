"""The dashboard.   Start it (the API must be running too) with:

    python -m streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                    # so `import api_client` / `screens` work

import streamlit as st  # noqa: E402

import api_client  # noqa: E402
from screens import account, audit_log, departments, employees, login, overview, reports, ui, users  # noqa: E402

st.set_page_config(page_title="MNC Management System", page_icon=str(HERE / "assets" / "icon.png"),
                   layout="wide")

ui.inject_css()

# page name -> (function that draws it, roles allowed; None = every role)
PAGES = {
    "Overview": (overview.show, None),
    "Employees": (employees.show, None),
    "Departments": (departments.show, {"admin"}),
    "Reports": (reports.show, {"admin"}),
    "Audit log": (audit_log.show, {"admin"}),
    "Users": (users.show, {"admin"}),
    "My account": (account.show, None),
}


def main():
    if "token" not in st.session_state:
        login.show()
        return

    role = st.session_state["role"]
    allowed = [name for name, (_, roles) in PAGES.items() if roles is None or role in roles]

    with st.sidebar:
        st.image(str(HERE / "assets" / "logo.png"))
        with st.container(border=True):
            st.markdown(f"Signed in as **{st.session_state['username']}**  \n:blue-badge[{role}]")
        page = st.radio("Go to", allowed, key="nav")
        if st.button("Sign out", key="logout"):
            api_client.logout()
            st.rerun()

    try:
        PAGES[page][0]()
    except api_client.ApiError as err:           # anything a screen did not handle itself
        st.error(err.message)


main()

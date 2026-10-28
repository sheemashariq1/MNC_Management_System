"""The ONLY file of the dashboard that talks HTTP to the API.

Every screen calls the small functions below (employees(), create_employee(), ...).
The login token lives in st.session_state, so every browser tab has its own login.
"""
import os

import httpx
import streamlit as st

API_URL = os.getenv("MNC_API_URL", "http://127.0.0.1:8000")
_client = None

EXCEL_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ApiError(Exception):
    """The API said no (or could not be reached). `message` is safe to show to the user."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def http():
    """One shared HTTP client. (The tests swap this for the FastAPI TestClient.)"""
    global _client
    if _client is None:
        _client = httpx.Client(base_url=API_URL, timeout=20)
    return _client


# ------------------------------------------------------------------ session ----------------------------------------------------------------------
def logout(flash=None):
    for key in list(st.session_state.keys()):
        if key in ("token", "username", "role") or key.startswith("report_"):
            del st.session_state[key]
    if flash:
        st.session_state["_flash"] = ("warning", flash)


def _detail(response):
    """Pull a readable message out of an error response."""
    try:
        detail = response.json().get("detail")
    except Exception:                                   # not JSON at all
        detail = None
    if isinstance(detail, list):                        # 422: Pydantic validation errors
        parts = []
        for item in detail:
            where = ".".join(str(p) for p in item.get("loc", [])[1:])
            parts.append(f"{where}: {item.get('msg')}" if where else str(item.get("msg")))
        detail = "; ".join(parts)
    return detail or f"Server error ({response.status_code})"


def _request(method, path, **kwargs):
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = http().request(method, path, headers=headers, **kwargs)
    except httpx.TransportError:
        raise ApiError(0, "Cannot reach the API. Is it running?  "
                          "(python -m uvicorn api.main:app --reload)")
    if response.status_code == 401 and token:
        # token expired or the account was deleted: back to the login page
        logout("Your session has ended. Please sign in again.")
        st.rerun()
    if response.status_code >= 400:
        raise ApiError(response.status_code, _detail(response))
    return response


def _json(method, path, **kwargs):
    return _request(method, path, **kwargs).json()


def _download(path):
    response = _request("GET", path)
    disposition = response.headers.get("content-disposition", "")
    name = disposition.split("filename=")[-1].strip('"; ') if "filename=" in disposition else "report"
    return response.content, name


# --------------------------------------------------------------------- auth ------------------------------------------------------------------------
def login(username, password):
    return _json("POST", "/auth/login", data={"username": username, "password": password})


def register(username, password, access_code):
    return _json("POST", "/auth/register", json={
        "username": username, "password": password, "access_code": access_code})


def change_password(current_password, new_password):
    return _json("POST", "/auth/change-password", json={
        "current_password": current_password, "new_password": new_password})


# ---------------------------------------------------------------- employees -------------------------------------------------------------------------
def employees(search=None, department_id=None):
    params = {}
    if search:
        params["search"] = search
    if department_id is not None:
        params["department_id"] = department_id
    return _json("GET", "/employees", params=params)


def create_employee(payload):
    return _json("POST", "/employees", json=payload)


def update_employee(emp_id, changes):
    return _json("PATCH", f"/employees/{emp_id}", json=changes)


def transfer_employee(emp_id, department_id):
    return _json("POST", f"/employees/{emp_id}/transfer", json={"department_id": department_id})


def terminate_employee(emp_id):
    return _json("DELETE", f"/employees/{emp_id}")


# -------------------------------------------------------------- departments -----------------------------------------------------------------------------
def overview():
    return _json("GET", "/departments/overview")


def departments():
    return _json("GET", "/departments")


def add_department(name, code, floor):
    return _json("POST", "/departments", json={"name": name, "code": code, "floor": floor})


def update_department(dept_id, changes):
    return _json("PATCH", f"/departments/{dept_id}", json=changes)


def delete_department(dept_id):
    return _json("DELETE", f"/departments/{dept_id}")


# -------------------------------------------------------------------- users ------------------------------------------------------------------------------
def users():
    return _json("GET", "/users")


def change_role(username, role):
    return _json("PATCH", f"/users/{username}/role", json={"role": role})


def delete_user(username):
    return _json("DELETE", f"/users/{username}")


# ------------------------------------------------------------ reports, audit ------------------------------------------------------------------------------
def report_summary():
    return _json("GET", "/reports/summary")


def export_excel():
    return _download("/reports/export/excel")


def export_csv():
    return _download("/reports/export/csv")


def audit(limit=50, username=None, action=None):
    params = {"limit": limit}
    if username:
        params["username"] = username
    if action:
        params["action"] = action
    return _json("GET", "/audit", params=params)

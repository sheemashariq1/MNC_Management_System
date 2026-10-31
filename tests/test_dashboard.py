""" Dashboard tests.

Streamlit's AppTest runs the REAL dashboard script without a browser. The dashboard's
HTTP client is pointed at the FastAPI TestClient, so every click goes through the
real API, the real services and the (test) database.
"""
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
import api_client  # noqa: E402

import database  # noqa: E402
import reports as reports_module  # noqa: E402
from api.main import app as api_app  # noqa: E402

APP = str(ROOT / "dashboard" / "app.py")
PASSWORD = "secret12"


@pytest.fixture
def api(codes, monkeypatch):
    """The API (in memory). The dashboard's HTTP client is switched to it."""
    client = TestClient(api_app)
    monkeypatch.setattr(api_client, "http", lambda: client)
    return client


def make_user(api, username, code):
    r = api.post("/auth/register", json={"username": username, "password": PASSWORD,
                                         "access_code": code})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture
def admin(api):
    return make_user(api, "boss", "ADM")


def hire_via_api(api, headers, name, department_id, salary=50000, **extra):
    r = api.post("/employees", headers=headers, json={
        "name": name, "designation": "Manager", "salary": salary,
        "department_id": department_id, **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def open_app():
    return AppTest.from_file(APP, default_timeout=30).run()


def sign_in(username, password=PASSWORD):
    at = open_app()
    at.text_input(key="login_username").input(username)
    at.text_input(key="login_password").input(password)
    at.button(key="login_submit").click().run()
    assert not at.exception, at.exception
    return at


def goto(at, page):
    at.sidebar.radio(key="nav").set_value(page).run()
    assert not at.exception, at.exception
    return at


def texts(elements):
    return [e.value for e in elements]


# ============================================================== login / logout ==================================================================
def test_login_page_is_shown_first(api):
    at = open_app()
    assert texts(at.title) == ["MNC Management System"]
    assert "token" not in at.session_state


def test_wrong_password_shows_an_error(api, admin):
    at = open_app()
    at.text_input(key="login_username").input("boss")
    at.text_input(key="login_password").input("wrong-password")
    at.button(key="login_submit").click().run()
    assert texts(at.error) == ["Wrong username or password."]
    assert "token" not in at.session_state


def test_sign_in_then_sign_out(api, admin):
    at = sign_in("boss")
    assert at.session_state["role"] == "admin"
    at.button(key="logout").click().run()
    assert "token" not in at.session_state
    assert texts(at.title) == ["MNC Management System"]            # back on the login page


def test_create_account_from_the_dashboard(api):
    at = open_app()
    at.text_input(key="reg_username").input("newhr")
    at.text_input(key="reg_password").input(PASSWORD)
    at.text_input(key="reg_confirm").input(PASSWORD)
    at.text_input(key="reg_code").input("HRC")
    at.button(key="reg_submit").click().run()
    assert at.session_state["role"] == "hr" and at.session_state["username"] == "newhr"


def test_registration_checks(api):
    at = open_app()
    at.text_input(key="reg_username").input("newhr")
    at.text_input(key="reg_password").input(PASSWORD)
    at.text_input(key="reg_confirm").input("different")
    at.text_input(key="reg_code").input("HRC")
    at.button(key="reg_submit").click().run()
    assert "do not match" in texts(at.error)[0]
    at.text_input(key="reg_confirm").input(PASSWORD)
    at.text_input(key="reg_code").input("WRONG")
    at.button(key="reg_submit").click().run()
    assert texts(at.error) == ["Invalid access code."]


def test_expired_session_sends_you_back_to_login(api, admin):
    at = sign_in("boss")
    database.run("delete from users where username = %s", ("boss",))   # account vanishes
    goto(at, "Employees")                                             # any call now gets a 401
    assert "token" not in at.session_state
    assert any("session has ended" in w.value for w in at.warning)
    assert texts(at.title) == ["MNC Management System"]


def test_api_not_running_gives_a_friendly_message(monkeypatch):
    class Dead:
        def request(self, *args, **kwargs):
            raise httpx.ConnectError("refused")
    monkeypatch.setattr(api_client, "http", lambda: Dead())
    at = open_app()
    at.text_input(key="login_username").input("boss")
    at.text_input(key="login_password").input(PASSWORD)
    at.button(key="login_submit").click().run()
    assert "Cannot reach the API" in texts(at.error)[0]


# ================================================================ role based menu ================================================================================
def test_admin_sees_every_page(api, admin):
    at = sign_in("boss")
    assert at.sidebar.radio(key="nav").options == [
        "Overview", "Employees", "Departments", "Reports", "Audit log", "Users", "My account"]


@pytest.mark.parametrize("username, code", [("hruser", "HRC"), ("ituser", "ITC")])
def test_hr_and_it_see_only_three_pages(api, username, code):
    make_user(api, username, code)
    at = sign_in(username)
    assert at.sidebar.radio(key="nav").options == ["Overview", "Employees", "My account"]


# ==================================================================== overview ==================================================================================
def test_overview_shows_live_numbers(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    hire_via_api(api, admin, "Meera", depts["IT"])
    hire_via_api(api, admin, "Imran", depts["IT"])
    at = sign_in("boss")
    metrics = {m.label: m.value for m in at.metric}
    assert metrics == {"Employees": "3", "Departments": "5", "Busiest department": "IT Department"}
    assert len(at.dataframe[0].value) == 5


# ================================================================== employees ======================================================================================
def test_hire_through_the_form(api, admin, depts, audit_entries):
    at = goto(sign_in("boss"), "Employees")
    at.text_input(key="hire_name_0").input("Neha")
    at.text_input(key="hire_designation_0").input("Analyst")
    at.selectbox(key="hire_dept_0").set_value("IT Department")
    at.button(key="hire_submit_0").click().run()
    assert not at.exception
    assert any("Hired Neha" in s.value for s in at.success)
    assert list(at.dataframe[0].value["name"]) == ["Neha"]
    assert at.dataframe[0].value.iloc[0]["department"] == "IT Department"
    assert any(a == "EMP_ADDED" and u == "boss" for u, _, a, _ in audit_entries())
    assert at.text_input(key="hire_name_1").value == ""             # the form is empty again


def test_hire_validation_error_is_shown(api, admin):
    at = goto(sign_in("boss"), "Employees")
    at.text_input(key="hire_designation_0").input("Analyst")        # name left empty
    at.button(key="hire_submit_0").click().run()
    assert any("cannot be empty" in e for e in texts(at.error))
    assert database.fetch("select count(*) from employees")[0][0] == 0


def test_search_and_department_filter(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    hire_via_api(api, admin, "Meera", depts["IT"])
    at = goto(sign_in("boss"), "Employees")
    assert sorted(at.dataframe[0].value["name"]) == ["Asha", "Meera"]
    at.text_input(key="emp_search").input("Meera").run()
    assert list(at.dataframe[0].value["name"]) == ["Meera"]
    at.text_input(key="emp_search").input("").run()
    at.selectbox(key="emp_dept_filter").set_value("HR Department").run()
    assert list(at.dataframe[0].value["name"]) == ["Asha"]


def test_hr_user_only_sees_the_hr_department(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    hire_via_api(api, admin, "Meera", depts["IT"])
    make_user(api, "hruser", "HRC")
    at = goto(sign_in("hruser"), "Employees")
    assert list(at.dataframe[0].value["name"]) == ["Asha"]
    assert "emp_dept_filter" not in [sb.key for sb in at.selectbox]  # no department filter for hr
    assert [t.label for t in at.tabs] == ["Edit", "Terminate"]       # no Transfer for hr
    # hiring without choosing a department puts the person into HR
    at.text_input(key="hire_name_0").input("Neha")
    at.text_input(key="hire_designation_0").input("Analyst")
    at.button(key="hire_submit_0").click().run()
    assert sorted(at.dataframe[0].value["name"]) == ["Asha", "Neha"]
    assert at.dataframe[0].value["department"].unique().tolist() == ["HR Department"]


def test_edit_sends_only_what_changed(api, admin, depts, audit_entries):
    emp_id = hire_via_api(api, admin, "Asha", depts["HR"], salary=50000)
    at = goto(sign_in("boss"), "Employees")
    at.button(key=f"edit_submit_{emp_id}").click().run()                 # nothing changed
    assert texts(at.info)[-1] == "Nothing changed."
    at.number_input(key=f"edit_salary_{emp_id}").set_value(60000)
    at.button(key=f"edit_submit_{emp_id}").click().run()
    assert any("Updated Asha" in s.value for s in at.success)
    row = at.dataframe[0].value.iloc[0]
    assert (row["name"], row["salary"]) == ("Asha", 60000)
    updates = [d for _, _, a, d in audit_entries() if a == "EMP_UPDATED"]
    assert len(updates) == 1 and "salary: 50000 -> 60000" in updates[0]


def test_edit_error_from_the_api_is_shown(api, admin, depts):
    emp_id = hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    at.text_input(key=f"edit_name_{emp_id}").input("x" * 31)             # longer than allowed
    at.button(key=f"edit_submit_{emp_id}").click().run()
    assert any("at most 30" in e for e in texts(at.error))


def test_transfer_is_admin_only_and_works(api, admin, depts):
    emp_id = hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    at.selectbox(key=f"transfer_to_{emp_id}").set_value("IT Department")
    at.button(key=f"transfer_go_{emp_id}").click().run()
    assert any("moved to IT Department" in s.value for s in at.success)
    assert at.dataframe[0].value.iloc[0]["department"] == "IT Department"


def test_terminate_needs_the_checkbox(api, admin, depts):
    emp_id = hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    assert at.button(key=f"term_go_{emp_id}").disabled
    at.checkbox(key=f"term_sure_{emp_id}").set_value(True).run()
    assert not at.button(key=f"term_go_{emp_id}").disabled
    at.button(key=f"term_go_{emp_id}").click().run()
    assert any("was terminated" in s.value for s in at.success)
    assert database.fetch("select count(*) from employees")[0][0] == 0


# ================================================================== departments
def test_department_add_and_duplicate_error(api, admin):
    at = goto(sign_in("boss"), "Departments")
    at.text_input(key="dept_name_0").input("Finance")
    at.text_input(key="dept_code_0").input("fin")
    at.number_input(key="dept_floor_0").set_value(6)
    at.button(key="dept_add_submit_0").click().run()
    assert any("Finance added" in s.value for s in at.success)
    assert "Finance" in list(at.dataframe[0].value["name"])
    at.text_input(key="dept_name_1").input("Finance")
    at.text_input(key="dept_code_1").input("fin2")
    at.button(key="dept_add_submit_1").click().run()
    assert any("already exists" in e for e in texts(at.error))


def test_cannot_delete_a_department_with_employees(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Departments")
    at.selectbox(key="dept_pick").select_index(1).run()                # HR Department (id order)
    did = depts["HR"]
    at.checkbox(key=f"dept_sure_{did}").set_value(True).run()
    at.button(key=f"dept_delete_{did}").click().run()
    assert any("Cannot delete" in e for e in texts(at.error))


# ======================================================================== users ==========================================================================
def test_users_page_protects_the_last_admin(api, admin):
    make_user(api, "hruser", "HRC")
    at = goto(sign_in("boss"), "Users")
    assert sorted(at.dataframe[0].value["username"]) == ["boss", "hruser"]
    at.selectbox(key="role_user").set_value("boss")
    at.selectbox(key="role_new").set_value("hr")
    at.button(key="role_submit").click().run()
    assert any("LAST admin" in e for e in texts(at.error))
    at.selectbox(key="role_user").set_value("hruser")
    at.selectbox(key="role_new").set_value("it")
    at.button(key="role_submit").click().run()
    assert any("hruser is now it" in s.value for s in at.success)


# ================================================================ audit + reports ==========================================================================
def test_audit_page_filters(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Audit log")
    assert "EMP_ADDED" in list(at.dataframe[0].value["action"])
    at.text_input(key="audit_action").input("EMP_").run()
    assert set(at.dataframe[0].value["action"]) == {"EMP_ADDED"}
    at.text_input(key="audit_user").input("nobody").run()
    assert texts(at.info) == ["No entries match."]


def test_reports_page_summary_and_download_button(api, admin, depts, tmp_path, monkeypatch):
    monkeypatch.setattr(reports_module, "REPORT_DIR", tmp_path)
    assert texts(goto(sign_in("boss"), "Reports").info) == [
        "There are no employees yet, so there is nothing to report."]
    hire_via_api(api, admin, "Asha", depts["HR"])
    hire_via_api(api, admin, "Meera", depts["IT"], salary=70000)
    at = goto(sign_in("boss"), "Reports")
    summary = at.dataframe[0].value.set_index("Department")
    assert summary.loc["IT Department", "Highest salary"] == 70000
    assert not at.get("download_button")                                # nothing prepared yet
    at.button(key="report_excel_prepare").click().run()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label.endswith(".xlsx")
    assert list(tmp_path.glob("*.xlsx"))                                # the API really wrote it


# ====================================================================== account =============================================================================
def test_change_password_from_the_dashboard(api, admin):
    at = goto(sign_in("boss"), "My account")
    at.text_input(key="pw_current").input(PASSWORD)
    at.text_input(key="pw_new").input("brandnew1")
    at.text_input(key="pw_confirm").input("different")
    at.button(key="pw_submit").click().run()
    assert "do not match" in texts(at.error)[0]
    at.text_input(key="pw_confirm").input("brandnew1")
    at.button(key="pw_submit").click().run()
    assert texts(at.success) == ["Password changed."]
    assert api.post("/auth/login", data={"username": "boss", "password": "brandnew1"}).status_code == 200
    assert api.post("/auth/login", data={"username": "boss", "password": PASSWORD}).status_code == 401


# ============================================================ friendly empty states ===========================================================================
def test_overview_has_a_friendly_empty_state(api, admin):
    at = sign_in("boss")                                              # nobody hired yet
    assert any("No employees yet" in i.value for i in at.info)


def test_search_with_no_match_shows_a_hint(api, admin, depts):
    hire_via_api(api, admin, "Asha", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    at.text_input(key="emp_search").input("zzz-nobody").run()
    assert any("No employees found" in i.value for i in at.info)

def test_employee_table_is_paged(api, admin, depts):
    for i in range(30):
        hire_via_api(api, admin, f"Person {i:02d}", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    assert len(at.dataframe[0].value) == 25
    assert any("Showing 1-25 of 30" in c.value for c in at.caption)
    assert at.button(key="emp_prev").disabled

    at.button(key="emp_next").click().run()
    assert list(at.dataframe[0].value["name"]) == [f"Person {i:02d}" for i in range(25, 30)]
    assert any("Showing 26-30 of 30" in c.value for c in at.caption)
    assert at.button(key="emp_next").disabled

    at.text_input(key="emp_search").input("Person 07").run()      # a new search starts at page 1
    assert list(at.dataframe[0].value["name"]) == ["Person 07"]
    assert any("Showing 1-1 of 1" in c.value for c in at.caption)


def test_changing_rows_per_page_goes_back_to_the_first_page(api, admin, depts):
    for i in range(30):
        hire_via_api(api, admin, f"Person {i:02d}", depts["HR"])
    at = goto(sign_in("boss"), "Employees")
    at.button(key="emp_next").click().run()
    at.selectbox(key="emp_page_size").set_value(10).run()
    assert len(at.dataframe[0].value) == 10
    assert any("Page 1 of 3" in c.value for c in at.caption)
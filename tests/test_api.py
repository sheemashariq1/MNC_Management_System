"""API tests: every request goes through the real FastAPI app and the real (test) database."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

import config
import database
import reports
from api import security
from api.main import app

SECRET = config.JWT_SECRET


@pytest.fixture
def client(codes):
    return TestClient(app)


def register(client, username, code, password="secret12"):
    r = client.post("/auth/register", json={"username": username, "password": password,
                                            "access_code": code})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture
def admin(client):
    return register(client, "boss", "ADM")


@pytest.fixture
def hr(client):
    return register(client, "hruser", "HRC")


@pytest.fixture
def it(client):
    return register(client, "ituser", "ITC")


def hire(client, headers, name="Asha", **extra):
    body = {"name": name, "designation": "Manager", "salary": 50000, **extra}
    return client.post("/employees", json=body, headers=headers)


# ================================================================ health + auth =================================================================
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_returns_token_and_role_from_access_code(client):
    r = client.post("/auth/register", json={"username": "hruser", "password": "secret12",
                                            "access_code": "HRC"})
    assert r.status_code == 201
    assert r.json()["role"] == "hr" and r.json()["token_type"] == "bearer"
    me = client.get("/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]})
    assert me.json() == {"username": "hruser", "role": "hr"}


@pytest.mark.parametrize("body, status", [
    ({"username": "newuser", "password": "secret12", "access_code": "WRONG"}, 403),
    ({"username": "newuser", "password": "123", "access_code": "HRC"}, 400),
    ({"username": "ab", "password": "secret12", "access_code": "HRC"}, 400),
])
def test_register_errors(client, body, status):
    assert client.post("/auth/register", json=body).status_code == status


def test_register_duplicate_is_409(client, hr):
    r = client.post("/auth/register", json={"username": "hruser", "password": "secret12",
                                            "access_code": "HRC"})
    assert r.status_code == 409


def test_login_with_form_fields(client, hr):
    ok = client.post("/auth/login", data={"username": "hruser", "password": "secret12"})
    assert ok.status_code == 200 and ok.json()["role"] == "hr"
    assert client.post("/auth/login", data={"username": "hruser", "password": "no"}).status_code == 401
    assert client.post("/auth/login", data={"username": "ghost", "password": "secret12"}).status_code == 401


def test_account_is_locked_after_5_wrong_passwords(client, hr):
    for _ in range(5):
        assert client.post("/auth/login", data={"username": "hruser", "password": "bad"}).status_code == 401
    right = client.post("/auth/login", data={"username": "hruser", "password": "secret12"})
    assert right.status_code == 429                      # even the RIGHT password is refused now


def test_change_password_over_api(client, hr):
    body = {"current_password": "secret12", "new_password": "brandnew1"}
    assert client.post("/auth/change-password", json=body, headers=hr).status_code == 200
    assert client.post("/auth/login", data={"username": "hruser", "password": "secret12"}).status_code == 401
    assert client.post("/auth/login", data={"username": "hruser", "password": "brandnew1"}).status_code == 200
    bad = {"current_password": "wrong", "new_password": "another12"}
    assert client.post("/auth/change-password", json=bad, headers=hr).status_code == 400


# ===================================================================== tokens ============================================================================
def test_no_token_or_garbage_token_is_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/employees").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def _token(payload, key=SECRET, algorithm="HS256"):
    return {"Authorization": "Bearer " + jwt.encode(payload, key, algorithm=algorithm)}


def _payload(username="boss", minutes=10):
    now = datetime.now(timezone.utc)
    return {"sub": username, "iat": now, "exp": now + timedelta(minutes=minutes)}


def test_forged_expired_and_unsigned_tokens_are_rejected(client, admin):
    assert client.get("/auth/me", headers=_token(_payload())).status_code == 200      # control
    assert client.get("/auth/me", headers=_token(_payload(), key="y" * 40)).status_code == 401
    assert client.get("/auth/me", headers=_token(_payload(minutes=-1))).status_code == 401
    assert client.get("/auth/me", headers=_token(_payload(), key=None, algorithm="none")).status_code == 401
    no_exp = {"sub": "boss"}
    assert client.get("/auth/me", headers=_token(no_exp)).status_code == 401


def test_token_of_a_deleted_account_stops_working(client, admin, hr):
    assert client.get("/auth/me", headers=hr).status_code == 200
    assert client.delete("/users/hruser", headers=admin).status_code == 200
    assert client.get("/auth/me", headers=hr).status_code == 401


def test_role_change_takes_effect_immediately(client, admin, hr):
    assert client.get("/users", headers=hr).status_code == 403
    client.patch("/users/hruser/role", json={"role": "admin"}, headers=admin)
    assert client.get("/users", headers=hr).status_code == 200      # SAME old token, new role


def test_token_helper_needs_a_long_secret(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        security.create_access_token("boss")


# ================================================================== employees ===============================================================================
def test_employee_crud_as_admin(client, admin, depts):
    r = hire(client, admin, department_id=depts["IT"], field="Backend", date_of_joining="2024-08-15")
    assert r.status_code == 201
    emp = r.json()
    assert emp["department"] == "IT Department" and emp["date_of_joining"] == "2024-08-15"
    emp_id = emp["id"]
    assert client.get(f"/employees/{emp_id}", headers=admin).json()["name"] == "Asha"

    patched = client.patch(f"/employees/{emp_id}", json={"salary": 60000, "field": None}, headers=admin)
    assert patched.json()["salary"] == 60000 and patched.json()["field"] is None
    assert client.delete(f"/employees/{emp_id}", headers=admin).status_code == 200
    assert client.get(f"/employees/{emp_id}", headers=admin).status_code == 404


def test_patch_is_all_or_nothing(client, admin, depts):
    emp_id = hire(client, admin, department_id=depts["HR"]).json()["id"]
    bad = client.patch(f"/employees/{emp_id}", json={"name": "Changed", "salary": -5}, headers=admin)
    assert bad.status_code == 400
    assert client.get(f"/employees/{emp_id}", headers=admin).json()["name"] == "Asha"   # name NOT changed
    assert client.patch(f"/employees/{emp_id}", json={}, headers=admin).status_code == 400


def test_validation_errors(client, admin, depts):
    wrong_type = client.post("/employees", json={"name": "A", "designation": "B", "salary": "lots",
                                                 "department_id": depts["HR"]}, headers=admin)
    assert wrong_type.status_code == 422                 # FastAPI/Pydantic: wrong JSON type
    assert hire(client, admin, name="  ", department_id=depts["HR"]).status_code == 400   # our rule
    assert hire(client, admin).status_code == 400                                          # no department
    assert hire(client, admin, department_id=9999).status_code == 404
    assert client.get("/employees/9999", headers=admin).status_code == 404


def test_search_and_sql_injection_in_query(client, admin, depts):
    hire(client, admin, name="Asha", department_id=depts["HR"])
    hire(client, admin, name="Meera", department_id=depts["IT"])
    assert [e["name"] for e in client.get("/employees?search=Meera", headers=admin).json()] == ["Meera"]
    assert client.get("/employees?search=x' OR '1'='1", headers=admin).json() == []
    assert len(client.get("/employees", headers=admin).json()) == 2
    assert database.fetch("select count(*) from employees")[0][0] == 2


def test_transfer(client, admin, depts):
    emp_id = hire(client, admin, department_id=depts["HR"]).json()["id"]
    ok = client.post(f"/employees/{emp_id}/transfer", json={"department_id": depts["IT"]}, headers=admin)
    assert ok.json()["department"] == "IT Department"
    again = client.post(f"/employees/{emp_id}/transfer", json={"department_id": depts["IT"]}, headers=admin)
    assert again.status_code == 409
    missing = client.post(f"/employees/{emp_id}/transfer", json={"department_id": 9999}, headers=admin)
    assert missing.status_code == 404


# ============================================================ roles and scope ============================================================================
def test_hr_sees_and_changes_only_the_hr_department(client, admin, hr, depts):
    own = hire(client, admin, name="Asha", department_id=depts["HR"]).json()["id"]
    other = hire(client, admin, name="Meera", department_id=depts["IT"]).json()["id"]

    assert [e["name"] for e in client.get("/employees", headers=hr).json()] == ["Asha"]
    assert client.get(f"/employees/{own}", headers=hr).status_code == 200
    assert client.get(f"/employees/{other}", headers=hr).status_code == 403
    assert client.get(f"/employees?department_id={depts['IT']}", headers=hr).status_code == 403
    assert client.patch(f"/employees/{other}", json={"salary": 1}, headers=hr).status_code == 403
    assert client.delete(f"/employees/{other}", headers=hr).status_code == 403
    assert hire(client, hr, name="X", department_id=depts["IT"]).status_code == 403

    created = hire(client, hr, name="Neha")                  # no department_id -> HR by default
    assert created.status_code == 201 and created.json()["department"] == "HR Department"


def test_it_role_is_limited_to_it(client, admin, it, depts):
    hire(client, admin, name="Asha", department_id=depts["HR"])
    hire(client, admin, name="Meera", department_id=depts["IT"])
    assert [e["name"] for e in client.get("/employees", headers=it).json()] == ["Meera"]


@pytest.mark.parametrize("url", ["/users", "/audit", "/departments", "/reports/summary",
                                 "/reports/export/excel", "/reports/export/csv"])
def test_hr_and_it_are_blocked_from_admin_endpoints(client, hr, it, url):
    assert client.get(url, headers=hr).status_code == 403
    assert client.get(url, headers=it).status_code == 403


def test_every_role_can_see_the_building_overview(client, admin, hr, it):
    for headers in (admin, hr, it):
        rows = client.get("/departments/overview", headers=headers).json()
        assert len(rows) == 5 and {"floor", "department", "employees"} <= rows[0].keys()


# ========================================================= audit uses the TOKEN's user ==========================================================================
def test_audit_records_who_called_the_api(client, admin, hr, it, depts):
    hire(client, hr, name="ByHr")
    hire(client, it, name="ByIt")
    hire(client, admin, name="ByAdmin", department_id=depts["HR"])
    rows = client.get("/audit?action=EMP_ADDED", headers=admin).json()
    actors = {r["details"].split()[1]: (r["username"], r["role"]) for r in rows}
    assert actors == {"ByHr": ("hruser", "hr"), "ByIt": ("ituser", "it"), "ByAdmin": ("boss", "admin")}


def test_audit_filters_and_limit(client, admin, hr):
    assert client.get("/audit?limit=0", headers=admin).status_code == 422
    assert client.get("/audit?limit=501", headers=admin).status_code == 422
    only_hr = client.get("/audit?username=hruser", headers=admin).json()
    assert only_hr and all(r["username"] == "hruser" for r in only_hr)
    assert len(client.get("/audit?limit=1", headers=admin).json()) == 1


# =================================================================== departments ================================================================================
def test_department_management(client, admin, hr, depts):
    assert client.post("/departments", json={"name": "Finance", "code": "fin", "floor": 6},
                       headers=hr).status_code == 403
    created = client.post("/departments", json={"name": "Finance", "code": "fin", "floor": 6}, headers=admin)
    assert created.status_code == 201
    dup = client.post("/departments", json={"name": "Finance", "code": "xx", "floor": 6}, headers=admin)
    assert dup.status_code == 409
    listing = client.get("/departments", headers=admin).json()
    assert [d["name"] for d in listing][-1] == "Finance"
    assert client.delete(f"/departments/{created.json()['id']}", headers=admin).status_code == 200


def test_department_patch_is_all_or_nothing_and_delete_is_protected(client, admin, depts):
    clash = client.patch(f"/departments/{depts['OPS']}", json={"name": "HR Department", "floor": 9},
                         headers=admin)
    assert clash.status_code == 409
    floors = {d["name"]: d["floor"] for d in client.get("/departments", headers=admin).json()}
    assert floors["Operation and Maintenance"] == 4                  # floor was NOT changed
    hire(client, admin, department_id=depts["HR"])
    assert client.delete(f"/departments/{depts['HR']}", headers=admin).status_code == 409
    assert client.patch(f"/departments/{depts['OPS']}", json={}, headers=admin).status_code == 400


# ======================================================================== users ==================================================================================
def test_user_management(client, admin, hr):
    assert {u["username"]: u["role"] for u in client.get("/users", headers=admin).json()} == \
        {"boss": "admin", "hruser": "hr"}
    assert client.patch("/users/hruser/role", json={"role": "boss"}, headers=admin).status_code == 400
    assert client.patch("/users/ghost/role", json={"role": "it"}, headers=admin).status_code == 404
    assert client.patch("/users/boss/role", json={"role": "hr"}, headers=admin).status_code == 409   # last admin
    assert client.delete("/users/boss", headers=admin).status_code == 409                           # yourself


# ===================================================================== reports ===================================================================================
def test_reports(client, admin, depts, tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "REPORT_DIR", tmp_path)
    assert client.get("/reports/summary", headers=admin).json() == []
    assert client.get("/reports/export/excel", headers=admin).status_code == 400   # nothing to export
    hire(client, admin, name="Asha", department_id=depts["HR"], date_of_joining="2024-08-15")
    hire(client, admin, name="Meera", salary=70000, department_id=depts["IT"])    # no joining date

    summary = client.get("/reports/summary", headers=admin).json()
    by_name = {row["Department"]: row for row in summary}
    assert len(summary) == 5 and by_name["IT Department"]["Highest salary"] == 70000
    assert by_name["IT Department"]["Avg years of service"] is None               # blank -> null

    xlsx = client.get("/reports/export/excel", headers=admin)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"                  # a real .xlsx (zip)
    csv = client.get("/reports/export/csv", headers=admin)
    assert csv.status_code == 200 and "Asha" in csv.text

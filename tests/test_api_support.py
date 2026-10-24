"""Smaller pieces behind the API: error mapping, sessions per request, thread safety, lockout."""
import threading
from datetime import date

import pytest

import audit
import database
import session
from api.errors import status_for
from services import ServiceError, auth_service as auth, department_service as dep, employee_service as emp


# ------------------------------------------------------------- error -> status
@pytest.mark.parametrize("message, status", [
    ("Wrong username or password.", 401),
    ("Too many failed attempts. Try again in 15 minutes.", 429),
    ("Invalid access code.", 403),
    ("No such employee.", 404),
    ("Department does not exist.", 404),
    ("That user name is already taken.", 409),
    ("A department with this name already exists.", 409),
    ("Cannot delete IT Department: 1 employee(s) still work there.", 409),
    ("Cannot do that: this is the LAST admin account.", 409),
    ("You cannot delete the account you are logged in with.", 409),
    ("Salary must be a whole number (0 or more).", 400),
    ("Password is too short (min 6 characters).", 400),
])
def test_status_for(message, status):
    assert status_for(message) == status


# ------------------------------------------------- session is per thread / request
def test_session_is_not_shared_between_threads():
    session.login_user("main-user", "admin")
    seen = {}

    def other_thread():
        seen["before"] = session.username()          # a new thread starts with nobody logged in
        session.login_user("thread-user", "hr")
        seen["after"] = session.username()

    t = threading.Thread(target=other_thread)
    t.start()
    t.join()
    assert seen == {"before": None, "after": "thread-user"}
    assert session.username() == "main-user"         # the other thread did not leak into ours


def test_role_can_works_without_a_session():
    assert session.role_can("hr", "hr") and not session.role_can("hr", "audit")
    assert not session.role_can(None, "overview")


# --------------------------------------------------------------- thread safety
def test_many_threads_can_add_employees_at_the_same_time(depts):
    """20 threads x 5 inserts on ONE shared connection: no mix-ups, no lost rows, correct ids."""
    results, errors = {}, []

    def worker(n):
        try:
            session.login_user(f"user{n}", "admin")
            for i in range(5):
                name = f"T{n}-{i}"
                results[name] = emp.add_employee(name, "Tester", None, 1000, date(2024, 1, 1),
                                                 depts["IT"])
        except Exception as err:          # noqa: BLE001  (we want to see ANY failure)
            errors.append(err)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(results) == 100 and len(set(results.values())) == 100        # 100 different ids
    for name, emp_id in results.items():                                    # id belongs to ITS name
        assert emp.get_employee(emp_id)[1] == name
    assert database.fetch("select count(*) from employees")[0][0] == 100
    for n in range(20):                                                     # audit: right actor
        rows = database.fetch("select count(*) from audit_log where action = 'EMP_ADDED' "
                              "and username = %s", (f"user{n}",))
        assert rows[0][0] == 5


# ---------------------------------------------------------------- new services
def test_update_employee_fields_is_all_or_nothing(hire, audit_entries):
    emp_id = hire("Neha", salary=42000)
    with pytest.raises(ServiceError):
        emp.update_employee_fields(emp_id, {"emp_name": "Changed", "salary": -1})
    assert emp.get_employee(emp_id)[1] == "Neha"
    emp.update_employee_fields(emp_id, {"emp_name": "Neha S", "salary": 45000})
    row = emp.get_employee(emp_id)
    assert (row[1], row[4]) == ("Neha S", 45000)
    updates = [d for _, _, a, d in audit_entries() if a == "EMP_UPDATED"]
    assert len(updates) == 2                                               # one audit line per field
    with pytest.raises(ServiceError, match="Nothing to update"):
        emp.update_employee_fields(emp_id, {})


def test_update_department_changes_both_or_neither(depts):
    with pytest.raises(ServiceError, match="already exists"):
        dep.update_department(depts["OPS"], name="HR Department", floor=9)
    assert database.fetch("select floor from departments where dept_code = 'OPS'")[0][0] == 4
    dep.update_department(depts["OPS"], name="Operations", floor=9)
    assert database.fetch("select dept_name, floor from departments where dept_code = 'OPS'")[0] \
        == ("Operations", 9)


def test_audit_search_filters():
    audit.log("A_ONE", "x", username="u1")
    audit.log("B_TWO", "y", username="u2")
    audit.log("A_THREE", "z", username="u1")
    assert [r[4] for r in audit.search(action="a_")] == ["A_THREE", "A_ONE"]      # newest first
    assert [r[4] for r in audit.search(username="u2")] == ["B_TWO"]
    assert len(audit.search(limit=2)) == 2


# ------------------------------------------------------------------- lockout
def _fail(username, times):
    for _ in range(times):
        with pytest.raises(ServiceError, match="Wrong username or password"):
            auth.authenticate(username, "wrong-password")


def test_lockout_after_5_failures_even_for_the_right_password(codes, audit_entries):
    auth.register_user("hruser", "hrpass1", "HRC")
    _fail("hruser", 5)
    with pytest.raises(ServiceError, match="Too many failed attempts"):
        auth.authenticate("hruser", "hrpass1")
    assert "LOGIN_BLOCKED" in [a for _, _, a, _ in audit_entries()]


def test_lockout_is_per_user(codes):
    auth.register_user("hruser", "hrpass1", "HRC")
    auth.register_user("ituser", "itpass1", "ITC")
    _fail("hruser", 5)
    assert auth.authenticate("ituser", "itpass1") == "it"


def test_successful_login_resets_the_failure_count(codes):
    auth.register_user("hruser", "hrpass1", "HRC")
    _fail("hruser", 4)
    assert auth.authenticate("hruser", "hrpass1") == "hr"        # success resets the counter
    _fail("hruser", 4)                                           # 4 again: still not locked
    assert auth.authenticate("hruser", "hrpass1") == "hr"

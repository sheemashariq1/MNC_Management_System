import pytest

import database
from services import ServiceError, department_service as dep


def test_five_starting_departments_exist():
    assert [r[1] for r in dep.list_departments()] == [
        "Reception and Lobby", "HR Department", "IT Department",
        "Operation and Maintenance", "Cafeteria and Recreation Hall"]
    assert dep.get_by_code("HR")[1] == "HR Department"
    assert dep.get_by_code("NOPE") is None


def test_add_department_and_audit(audit_entries):
    new_id = dep.add_department("Finance", "fin", 6)           # code is stored upper-case
    assert dep.get_by_code("FIN") == (new_id, "Finance")
    assert audit_entries()[-1][2:] == ("DEPT_ADDED", "FIN Finance, floor 6")


@pytest.mark.parametrize("args, message", [
    (("HR Department", "XX", 1), "already exists"),            # duplicate name
    (("Finance", "HR", 1), "already used"),                    # duplicate code
    (("", "FIN", 1), "1-40"),
    (("Finance", "", 1), "1-10"),
    (("Finance", "FIN", -1), "Floor"),
    (("Finance", "FIN", True), "Floor"),
])
def test_add_department_rejects_bad_input(args, message):
    before = len(dep.list_departments())
    with pytest.raises(ServiceError, match=message):
        dep.add_department(*args)
    assert len(dep.list_departments()) == before


def test_rename_and_set_floor(depts):
    dep.rename_department(depts["OPS"], "Operations")
    dep.set_floor(depts["OPS"], 9)
    assert dep.get_by_code("OPS")[1] == "Operations"
    assert database.fetch("select floor from departments where dept_code = 'OPS'")[0][0] == 9
    with pytest.raises(ServiceError, match="already exists"):
        dep.rename_department(depts["OPS"], "HR Department")
    with pytest.raises(ServiceError, match="does not exist"):
        dep.set_floor(9999, 1)


def test_cannot_delete_department_with_employees(hire, depts):
    emp_id = hire("Asha", dept="HR")
    with pytest.raises(ServiceError, match="1 employee"):
        dep.delete_department(depts["HR"])
    assert dep.get_by_code("HR") is not None
    from services import employee_service
    employee_service.terminate_employee(emp_id)
    dep.delete_department(depts["HR"])                         # empty now: allowed
    assert dep.get_by_code("HR") is None


def test_overview_counts_are_live_and_include_empty_departments(hire):
    assert {name: n for _, name, n in dep.overview_rows()}["IT Department"] == 0
    hire("Meera", dept="IT")
    hire("Imran", dept="IT")
    counts = {name: n for _, name, n in dep.overview_rows()}
    assert counts["IT Department"] == 2
    assert counts["Reception and Lobby"] == 0                  # LEFT JOIN keeps empty ones


def test_database_foreign_key_protects_the_data(hire, depts):
    """The DATABASE itself refuses bad data, even if our Python code were buggy."""
    hire("Asha", dept="HR")
    assert database.run("insert into employees(emp_name, dept_id) values ('Ghost', 9999)") is None
    assert database.run("delete from departments where dept_id = %s", (depts["HR"],)) is None

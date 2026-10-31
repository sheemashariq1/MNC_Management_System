from datetime import date

import pytest

import database
from services import ServiceError, employee_service as emp


def test_add_employee_saves_row_and_audits(hire, audit_entries):
    emp_id = hire("Asha", salary=50000)
    row = emp.get_employee(emp_id)
    assert row[1] == "Asha" and row[4] == 50000 and row[6] == "HR Department"
    assert ("tester", "admin", "EMP_ADDED", f"id={emp_id} Asha -> HR Department, salary 50000") \
        in audit_entries()


@pytest.mark.parametrize("kwargs, message", [
    ({"name": "   "}, "cannot be empty"),
    ({"name": "x" * 31}, "at most 30"),
    ({"salary": -5}, "whole number"),
    ({"salary": "50000"}, "whole number"),       # text instead of a number
    ({"salary": True}, "whole number"),          # True is technically an int in Python!
])
def test_add_employee_rejects_bad_values(hire, kwargs, message):
    with pytest.raises(ServiceError, match=message):
        hire(**kwargs)
    assert emp.list_employees() == []


def test_add_employee_rejects_missing_department():
    with pytest.raises(ServiceError, match="Department does not exist"):
        emp.add_employee("Asha", "Manager", None, 1000, date(2024, 1, 1), 9999)


def test_sql_injection_text_is_stored_as_plain_text(hire):
    evil = "Robert'); DROP TABLE employees;--"
    emp_id = hire(evil[:30])
    assert emp.get_employee(emp_id)[1] == evil[:30]            # saved as ordinary text
    assert database.fetch("select count(*) from employees")[0][0] == 1   # table still alive
    assert emp.find_employees("x' OR '1'='1") == []            # injection finds nothing


def test_find_by_name_id_and_department(hire, depts):
    hr_id = hire("Asha", dept="HR")
    it_id = hire("Asha", dept="IT")
    hire("Meera", dept="IT")
    assert len(emp.find_employees("Asha")) == 2                # same name, two departments
    assert len(emp.find_employees("Asha", depts["HR"])) == 1   # limited to one department
    assert emp.find_employees(str(it_id))[0][0] == it_id       # a number searches the id too
    assert emp.find_employees("nobody") == []
    assert hr_id != it_id


def test_update_employee_and_audit_old_to_new(hire, audit_entries):
    emp_id = hire("Neha", salary=42000)
    emp.update_employee(emp_id, "salary", 45000)
    assert emp.get_employee(emp_id)[4] == 45000
    assert audit_entries()[-1][2:] == ("EMP_UPDATED",
                                       f"id={emp_id} Neha: salary: 42000 -> 45000")


def test_update_only_allows_whitelisted_columns(hire):
    emp_id = hire("Neha")
    for bad_column in ("dept_id", "emp_id", "salary = 0, emp_name", "x; drop table employees"):
        with pytest.raises(ServiceError, match="cannot be edited"):
            emp.update_employee(emp_id, bad_column, 1)
    assert emp.get_employee(emp_id)[4] == 50000                # nothing changed


def test_update_validates_value_and_employee(hire):
    emp_id = hire("Neha")
    with pytest.raises(ServiceError):
        emp.update_employee(emp_id, "salary", -1)
    with pytest.raises(ServiceError, match="No such employee"):
        emp.update_employee(9999, "salary", 1000)


def test_optional_field_can_be_cleared(hire):
    emp_id = hire("Meera", dept="IT", field="Backend")
    assert emp.get_employee(emp_id)[3] == "Backend"
    emp.update_employee(emp_id, "field", "")                   # empty text -> NULL
    assert emp.get_employee(emp_id)[3] is None


def test_transfer_employee(hire, depts, audit_entries):
    emp_id = hire("Neha", dept="HR")
    emp.transfer_employee(emp_id, depts["IT"])
    assert emp.get_employee(emp_id)[6] == "IT Department"
    assert audit_entries()[-1][2] == "EMP_TRANSFERRED"
    with pytest.raises(ServiceError, match="already works"):
        emp.transfer_employee(emp_id, depts["IT"])
    with pytest.raises(ServiceError, match="Department does not exist"):
        emp.transfer_employee(emp_id, 9999)


def test_terminate_employee(hire, audit_entries):
    emp_id = hire("Neha")
    emp.terminate_employee(emp_id)
    assert emp.get_employee(emp_id) is None
    assert audit_entries()[-1][2] == "EMP_TERMINATED"
    with pytest.raises(ServiceError, match="No such employee"):
        emp.terminate_employee(emp_id)


def test_list_employees_can_be_limited_to_one_department(hire, depts):
    hire("Asha", dept="HR")
    hire("Meera", dept="IT")
    assert [r[1] for r in emp.list_employees(depts["IT"])] == ["Meera"]
    assert len(emp.list_employees()) == 2

def test_employees_page_gives_rows_and_the_total(hire, depts):
    for i in range(7):
        hire(f"Person {i}", dept="HR" if i < 4 else "IT")
    rows, total = emp.employees_page(limit=3, offset=3)
    assert total == 7
    assert [r[1] for r in rows] == ["Person 3", "Person 4", "Person 5"]
    rows, total = emp.employees_page(dept_id=depts["IT"], limit=2)
    assert (len(rows), total) == (2, 3)
    assert emp.employees_page(key="Person 5")[1] == 1
    assert emp.employees_page(limit=5, offset=50) == ([], 7)
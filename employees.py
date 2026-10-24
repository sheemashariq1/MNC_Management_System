"""Employees, departments and reports (Step 2 schema).

employees.dept_id is a FOREIGN KEY -> departments.dept_id. So:
  * an employee can only belong to a department that really exists
  * a department that still has employees cannot be deleted by mistake
"""
import schema  # noqa: F401  (makes sure the tables exist)
import session
from helpers import (ask_text, ask_optional, ask_int, ask_date, ask_yes,
                     print_rows)
from services import ServiceError, department_service, employee_service
# re-export: reports.py aur MNC.py bina badle chalte rahenge
from services.department_service import overview_rows  # noqa: F401
from services.employee_service import COLUMN_RULES, EMP_HEADERS, EMP_SQL  # noqa: F401

# Menus kya edit kar sakte hain: service ke rules se bana (single source of truth)
EDITABLE = [
    (col, label, "optional" if kind == "text" and not required else kind, max_len)
    for col, (label, kind, max_len, required, _) in COLUMN_RULES.items()
]


# ------------------------------------------------------------- small helpers
def _ask_value(label, kind, max_len=None):
    prompt = f"enter {label}: "
    if kind == "int":
        return ask_int(prompt, minimum=0)
    if kind == "date":
        return ask_date(prompt)
    if kind == "optional":
        return ask_optional(prompt + "(Enter to leave empty) ", max_len)
    return ask_text(prompt, max_len)


def get_department(code):
    """Return (dept_id, dept_name) for a department code like 'HR', or None."""
    return department_service.get_by_code(code)


def choose_department():
    """Show all departments and let the user pick one. Returns (dept_id, dept_name)."""
    rows = department_service.list_departments()
    if not rows:
        print("No departments yet. Add one from the DEPARTMENTS menu first.")
        return None
    print_rows(["ID", "Department", "Floor"], rows)
    valid = {r[0]: r for r in rows}
    while True:
        dept_id = ask_int("enter department id: ", 1)
        if dept_id in valid:
            return valid[dept_id][0], valid[dept_id][1]
        print("No such department id.")


def _lookup(key, dept_id):
    return employee_service.find_employees(key, dept_id)


def _find_one(dept):
    """Ask for id or name and return exactly ONE employee row (or None)."""
    key = input("enter employee id or name: ").strip()
    if not key:
        print("Nothing entered.")
        return None
    rows = _lookup(key, dept[0] if dept else None)
    if not rows:
        print("No such record found")
        return None
    if len(rows) == 1:
        return rows[0]
    print("Several employees match, please pick one by Emp_id:")
    print_rows(EMP_HEADERS, rows)
    valid = {str(r[0]): r for r in rows}
    while True:
        chosen = input("enter the Emp_id to select: ").strip()
        if chosen in valid:
            return valid[chosen]
        print("That is not one of the listed employees.")


# --------------------------------------------------------- employee actions
def list_employees(dept):
    print_rows(EMP_HEADERS, employee_service.list_employees(dept[0] if dept else None))


def add_employee(dept):
    if dept is None:
        dept = choose_department()
        if dept is None:
            return
    while True:
        name = ask_text("enter employee name: ", 30)
        desig = ask_text("enter designation: ", 25)
        field = ask_optional("enter field / specialisation (Enter to skip): ", 25)
        salary = ask_int("enter salary: ", 0)
        doj = ask_date("enter date of joining ")
        try:
            new_id = employee_service.add_employee(name, desig, field, salary, doj, dept[0])
        except ServiceError as err:
            print(err)
        else:
            print(f"ADDED to {dept[1]}! New employee id = {new_id}")
        if not ask_yes("do you want to add more employees?"):
            break


def remove_employee(dept):
    while True:
        row = _find_one(dept)
        if row:
            print_rows(EMP_HEADERS, [row])
            if ask_yes("Are you sure you want to terminate this employee?"):
                try:
                    employee_service.terminate_employee(row[0])
                except ServiceError as err:
                    print(err)
                else:
                    print("RECORD DELETED!")
            else:
                print("Cancelled.")
        if not ask_yes("do you want to terminate more employees?"):
            break


def update_employee(dept):
    transfer_option = len(EDITABLE) + 1
    while True:
        row = _find_one(dept)
        if row:
            print_rows(EMP_HEADERS, [row])
            print("what do you want to update?")
            for i, (_, label, _, _) in enumerate(EDITABLE, 1):
                print(f"{i}-{label}")
            print(f"{transfer_option}-department (transfer to another department)")
            pick = ask_int("enter your choice: ", 1, transfer_option)
            if pick == transfer_option:
                new_dept = choose_department()
                if new_dept:
                    try:
                        employee_service.transfer_employee(row[0], new_dept[0])
                    except ServiceError as err:
                        print(err)
                    else:
                        print(f"TRANSFERRED to {new_dept[1]}!")
            else:
                col, label, kind, max_len = EDITABLE[pick - 1]
                value = _ask_value("new " + label, kind, max_len)
                try:
                    employee_service.update_employee(row[0], col, value)
                except ServiceError as err:
                    print(err)
                else:
                    print("UPDATED!")
        if not ask_yes("do you want to update more employees?"):
            break


def search_employee(dept):
    while True:
        key = input("enter employee id or name: ").strip()
        rows = _lookup(key, dept[0] if dept else None) if key else []
        if rows:
            print("Employee found!")
            print_rows(EMP_HEADERS, rows)
        else:
            print("No such record found")
        if not ask_yes("do you want to search for more employees?"):
            break


def employee_menu(dept, title):
    """dept = (dept_id, dept_name) to work inside ONE department, or None for all."""
    print(f"You can perform the following functions in {title}")
    while True:
        print("\n1-Hire new employee")
        print("2-Terminate an employee")
        print("3-Display employees")
        print("4-Update details of an employee")
        print("5-Search for an employee")
        print("6-Exit")
        choice = ask_int("Enter your choice: ", 1, 6)
        if choice == 1:
            add_employee(dept)
        elif choice == 2:
            remove_employee(dept)
        elif choice == 3:
            list_employees(dept)
        elif choice == 4:
            update_employee(dept)
        elif choice == 5:
            search_employee(dept)
        else:
            break


def _department_shortcut(code):
    dept = get_department(code)
    if dept is None:
        print(f"Department with code '{code}' does not exist (it may have been deleted).")
        return
    employee_menu(dept, dept[1].upper())


def hr():
    if session.require("hr"):
        _department_shortcut("HR")


def it():
    if session.require("it"):
        _department_shortcut("IT")


def all_employees():
    if session.require("all_employees"):
        employee_menu(None, "ALL EMPLOYEES (every department)")


# ------------------------------------------------------------- departments

def _add_department():
    name = ask_text("enter department name: ", 40)
    code = ask_text("enter a short unique code (e.g. FIN): ", 10)
    floor = ask_int("enter floor number: ", 0)
    try:
        department_service.add_department(name, code, floor)
    except ServiceError as err:
        print(err)
    else:
        print("DEPARTMENT ADDED!")


def _update_department():
    dept = choose_department()
    if dept is None:
        return
    print("1-name\n2-floor")
    pick = ask_int("what do you want to update? ", 1, 2)
    try:
        if pick == 1:
            department_service.rename_department(
                dept[0], ask_text("enter new department name: ", 40))
        else:
            department_service.set_floor(dept[0], ask_int("enter new floor number: ", 0))
    except ServiceError as err:
        print(err)
        return
    print("UPDATED!")


def _delete_department():
    dept = choose_department()
    if dept is None:
        return
    if ask_yes(f"Delete department '{dept[1]}'?"):
        try:
            department_service.delete_department(dept[0])
        except ServiceError as err:
            print(err)
        else:
            print("DEPARTMENT DELETED!")


def department_menu():
    if not session.require("departments"):
        return
    while True:
        print("\n1-View departments (with live employee count)")
        print("2-Add a department")
        print("3-Update a department")
        print("4-Delete a department")
        print("5-Back")
        choice = ask_int("Enter your choice: ", 1, 5)
        if choice == 1:
            print_rows(["ID", "Code", "Department", "Floor", "Employees"],
                       department_service.department_summary())
        elif choice == 2:
            _add_department()
        elif choice == 3:
            _update_department()
        elif choice == 4:
            _delete_department()
        else:
            break

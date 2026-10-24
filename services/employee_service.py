"""Employee rules + database work. No input() / print() in this file."""
from datetime import date

import audit
from database import last_id, run, fetch
from services import ServiceError

EMP_HEADERS = ["Emp_id", "Name", "Designation", "Field", "Salary", "Joined", "Department"]

# JOIN: take each employee row and attach its department name.
EMP_SQL = (
    "select e.emp_id, e.emp_name, e.designation, e.field, e.salary, "
    "e.date_of_joining, d.dept_name "
    "from employees e join departments d on e.dept_id = d.dept_id"
)

# column -> (label, kind, max_len, required, position of that column in an EMP_SQL row)
# This dict is also the WHITELIST of columns that may be edited.
COLUMN_RULES = {
    "emp_name":        ("employee name", "text", 30, True, 1),
    "designation":     ("designation", "text", 25, True, 2),
    "field":           ("field", "text", 25, False, 3),
    "salary":          ("salary", "int", None, True, 4),
    "date_of_joining": ("date of joining", "date", None, False, 5),
}


def _check(column, value):
    """Validate one value for one column. Returns the cleaned value."""
    label, kind, max_len, required, _ = COLUMN_RULES[column]
    if kind == "text":
        value = None if value is None else str(value).strip()
        if not value:
            if required:
                raise ServiceError(f"{label.capitalize()} cannot be empty.")
            return None
        if max_len and len(value) > max_len:
            raise ServiceError(f"{label.capitalize()} can have at most {max_len} characters.")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ServiceError(f"{label.capitalize()} must be a whole number (0 or more).")
        return value
    if value is not None and not isinstance(value, date):
        raise ServiceError("Date of joining must be a date.")
    return value


def _department_name(dept_id):
    rows = fetch("select dept_name from departments where dept_id = %s", (dept_id,))
    if not rows:
        raise ServiceError("Department does not exist.")
    return rows[0][0]


# ------------------------------------------------------------- reading
def get_employee(emp_id):
    rows = fetch(EMP_SQL + " where e.emp_id = %s", (emp_id,))
    return rows[0] if rows else None


def list_employees(dept_id=None):
    sql, params = EMP_SQL, ()
    if dept_id is not None:
        sql += " where e.dept_id = %s"
        params = (dept_id,)
    return fetch(sql + " order by e.emp_id", params)


def find_employees(key, dept_id=None):
    """Employees whose name (or id, if key is a number) matches. dept_id=None -> all."""
    sql = EMP_SQL + " where (e.emp_name = %s"
    params = [key]
    if key.isdigit():
        sql += " or e.emp_id = %s"
        params.append(int(key))
    sql += ")"
    if dept_id is not None:
        sql += " and e.dept_id = %s"
        params.append(dept_id)
    return fetch(sql + " order by e.emp_id", tuple(params))


# ------------------------------------------------------------- changing
def add_employee(name, designation, field, salary, joined, dept_id):
    """Hire someone. Returns the new emp_id."""
    name = _check("emp_name", name)
    designation = _check("designation", designation)
    field = _check("field", field)
    salary = _check("salary", salary)
    joined = _check("date_of_joining", joined)
    dept_name = _department_name(dept_id)
    saved = run(
        "insert into employees(emp_name, designation, field, salary, "
        "date_of_joining, dept_id) values (%s, %s, %s, %s, %s, %s)",
        (name, designation, field, salary, joined, dept_id),
    )
    if saved is None:
        raise ServiceError("Could not save the employee.")
    new_id = last_id()                # read it BEFORE logging (log() runs another insert)
    audit.log("EMP_ADDED", f"id={new_id} {name} -> {dept_name}, salary {salary}")
    return new_id


def update_employee_fields(emp_id, changes):
    """Change several columns of ONE employee: {"salary": 45000, "designation": "Lead"}.

    Everything is validated BEFORE anything is saved, so you never get a half update.
    """
    for column in changes:
        if column not in COLUMN_RULES:
            raise ServiceError("This column cannot be edited.")
    if not changes:
        raise ServiceError("Nothing to update.")
    row = get_employee(emp_id)
    if row is None:
        raise ServiceError("No such employee.")
    cleaned = {column: _check(column, value) for column, value in changes.items()}
    # the column names are safe to put in the SQL: they all passed the whitelist above
    assignments = ", ".join(f"{column} = %s" for column in cleaned)
    run(f"update employees set {assignments} where emp_id = %s", (*cleaned.values(), emp_id))
    for column, value in cleaned.items():
        label, _, _, _, position = COLUMN_RULES[column]
        audit.log("EMP_UPDATED", f"id={emp_id} {row[1]}: {label}: {row[position]} -> {value}")


def update_employee(emp_id, column, value):
    """Change ONE column of ONE employee."""
    update_employee_fields(emp_id, {column: value})


def transfer_employee(emp_id, new_dept_id):
    row = get_employee(emp_id)
    if row is None:
        raise ServiceError("No such employee.")
    new_name = _department_name(new_dept_id)
    if row[6] == new_name:
        raise ServiceError(f"This employee already works in {new_name}.")
    run("update employees set dept_id = %s where emp_id = %s", (new_dept_id, emp_id))
    audit.log("EMP_TRANSFERRED", f"id={emp_id} {row[1]}: {row[6]} -> {new_name}")


def terminate_employee(emp_id):
    row = get_employee(emp_id)
    if row is None:
        raise ServiceError("No such employee.")
    run("delete from employees where emp_id = %s", (emp_id,))
    audit.log("EMP_TERMINATED", f"id={emp_id} {row[1]} ({row[6]})")

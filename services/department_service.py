"""Department rules + database work. No input() / print() in this file."""
import audit
from database import run, fetch
from services import ServiceError


def get_by_code(code):
    """(dept_id, dept_name) for a code like 'HR', or None."""
    rows = fetch("select dept_id, dept_name from departments where dept_code = %s", (code,))
    return rows[0] if rows else None


def list_departments():
    """[(dept_id, dept_name, floor), ...]"""
    return fetch("select dept_id, dept_name, floor from departments order by dept_id")


def overview_rows():
    """Live headcount per floor/department: LEFT JOIN + COUNT + GROUP BY."""
    return fetch(
        "select d.floor, d.dept_name, count(e.emp_id) "
        "from departments d left join employees e on e.dept_id = d.dept_id "
        "group by d.dept_id, d.dept_name, d.floor "
        "order by d.floor, d.dept_name"
    )


def department_summary():
    return fetch(
        "select d.dept_id, d.dept_code, d.dept_name, d.floor, count(e.emp_id) "
        "from departments d left join employees e on e.dept_id = d.dept_id "
        "group by d.dept_id, d.dept_code, d.dept_name, d.floor "
        "order by d.dept_id"
    )


def _get(dept_id):
    rows = fetch("select dept_id, dept_name from departments where dept_id = %s", (dept_id,))
    if not rows:
        raise ServiceError("Department does not exist.")
    return rows[0]


def _check_name(name, dept_id=None):
    name = (name or "").strip()
    if not 1 <= len(name) <= 40:
        raise ServiceError("Department name must be 1-40 characters.")
    if fetch("select 1 from departments where dept_name = %s and dept_id <> %s",
             (name, dept_id or 0)):
        raise ServiceError("A department with this name already exists.")
    return name


def _check_floor(floor):
    if isinstance(floor, bool) or not isinstance(floor, int) or floor < 0:
        raise ServiceError("Floor must be a whole number (0 or more).")
    return floor


def add_department(name, code, floor):
    """Returns the new dept_id."""
    name = _check_name(name)
    code = (code or "").strip().upper()
    if not 1 <= len(code) <= 10:
        raise ServiceError("Department code must be 1-10 characters.")
    if fetch("select 1 from departments where dept_code = %s", (code,)):
        raise ServiceError("That code is already used.")
    floor = _check_floor(floor)
    if run("insert into departments(dept_code, dept_name, floor) values (%s, %s, %s)",
           (code, name, floor)) is None:
        raise ServiceError("Could not save the department.")
    new_id = fetch("select dept_id from departments where dept_code = %s", (code,))[0][0]
    audit.log("DEPT_ADDED", f"{code} {name}, floor {floor}")
    return new_id


def rename_department(dept_id, new_name):
    _, old_name = _get(dept_id)
    new_name = _check_name(new_name, dept_id)
    run("update departments set dept_name = %s where dept_id = %s", (new_name, dept_id))
    audit.log("DEPT_UPDATED", f"{old_name}: name -> {new_name}")


def set_floor(dept_id, floor):
    _, name = _get(dept_id)
    floor = _check_floor(floor)
    run("update departments set floor = %s where dept_id = %s", (floor, dept_id))
    audit.log("DEPT_UPDATED", f"{name}: floor -> {floor}")

def update_department(dept_id, name=None, floor=None):
    """Change name and/or floor together. Both are validated BEFORE anything is saved."""
    if name is None and floor is None:
        raise ServiceError("Nothing to update.")
    _, old_name = _get(dept_id)
    new_name = _check_name(name, dept_id) if name is not None else None
    new_floor = _check_floor(floor) if floor is not None else None
    if new_name is not None:
        run("update departments set dept_name = %s where dept_id = %s", (new_name, dept_id))
        audit.log("DEPT_UPDATED", f"{old_name}: name -> {new_name}")
    if new_floor is not None:
        run("update departments set floor = %s where dept_id = %s", (new_floor, dept_id))
        audit.log("DEPT_UPDATED", f"{new_name or old_name}: floor -> {new_floor}")

def delete_department(dept_id):
    """Only allowed when nobody works there any more."""
    _, name = _get(dept_id)
    count = fetch("select count(*) from employees where dept_id = %s", (dept_id,))[0][0]
    if count:
        raise ServiceError(f"Cannot delete {name}: {count} employee(s) still work there. "
                           "Transfer or terminate them first.")
    run("delete from departments where dept_id = %s", (dept_id,))
    audit.log("DEPT_DELETED", name)

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import CurrentUser, get_current_user
from api.schemas import EmployeeIn, EmployeeUpdate, TransferIn
from services import department_service, employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])

_ROLE_DEPARTMENT = {"hr": "HR", "it": "IT"}     # role -> code of the ONE department it may see
_FIELD_TO_COLUMN = {"name": "emp_name", "designation": "designation", "field": "field",
                    "salary": "salary", "date_of_joining": "date_of_joining"}


def _scope(user):
    """None = every department (admin). Otherwise (dept_id, dept_name) of the allowed one."""
    if user.role == "admin":
        return None
    dept = department_service.get_by_code(_ROLE_DEPARTMENT.get(user.role, ""))
    if dept is None:
        raise HTTPException(403, "Your department does not exist.")
    return dept


def _to_dict(row):
    emp_id, name, designation, field, salary, joined, department = row
    return {"id": emp_id, "name": name, "designation": designation, "field": field,
            "salary": salary, "date_of_joining": joined, "department": department}


def _visible_employee(emp_id, scope):
    """The employee row, or an HTTP error if it does not exist / is outside the user's scope."""
    row = employee_service.get_employee(emp_id)
    if row is None:
        raise HTTPException(404, "No such employee.")
    if scope is not None and row[6] != scope[1]:
        raise HTTPException(403, "This employee belongs to another department.")
    return row


@router.get("")
def list_employees(search: Optional[str] = None, department_id: Optional[int] = None,
                   user: CurrentUser = Depends(get_current_user)):
    """admin: everybody (optionally one department).  hr / it: only their own department."""
    scope = _scope(user)
    if scope is not None:
        if department_id not in (None, scope[0]):
            raise HTTPException(403, "You may only see your own department.")
        department_id = scope[0]
    rows = (employee_service.find_employees(search, department_id) if search
            else employee_service.list_employees(department_id))
    return [_to_dict(r) for r in rows]


@router.get("/{emp_id}")
def get_employee(emp_id: int, user: CurrentUser = Depends(get_current_user)):
    return _to_dict(_visible_employee(emp_id, _scope(user)))


@router.post("", status_code=201)
def create_employee(body: EmployeeIn, user: CurrentUser = Depends(get_current_user)):
    scope = _scope(user)
    dept_id = body.department_id
    if scope is not None:
        if dept_id not in (None, scope[0]):
            raise HTTPException(403, "You may only hire into your own department.")
        dept_id = scope[0]
    if dept_id is None:
        raise HTTPException(400, "department_id is required.")
    new_id = employee_service.add_employee(body.name, body.designation, body.field,
                                           body.salary, body.date_of_joining, dept_id)
    return _to_dict(employee_service.get_employee(new_id))


@router.patch("/{emp_id}")
def update_employee(emp_id: int, body: EmployeeUpdate,
                    user: CurrentUser = Depends(get_current_user)):
    _visible_employee(emp_id, _scope(user))
    sent = body.model_dump(exclude_unset=True)               # only the fields the client sent
    employee_service.update_employee_fields(
        emp_id, {_FIELD_TO_COLUMN[name]: value for name, value in sent.items()})
    return _to_dict(employee_service.get_employee(emp_id))


@router.post("/{emp_id}/transfer")
def transfer_employee(emp_id: int, body: TransferIn,
                      user: CurrentUser = Depends(get_current_user)):
    _visible_employee(emp_id, _scope(user))
    employee_service.transfer_employee(emp_id, body.department_id)
    return _to_dict(employee_service.get_employee(emp_id))


@router.delete("/{emp_id}")
def terminate_employee(emp_id: int, user: CurrentUser = Depends(get_current_user)):
    _visible_employee(emp_id, _scope(user))
    employee_service.terminate_employee(emp_id)
    return {"message": "Employee terminated.", "id": emp_id}

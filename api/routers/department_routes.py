from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_current_user, require_feature
from api.schemas import DepartmentIn, DepartmentUpdate
from services import department_service

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/overview")
def overview(user: CurrentUser = Depends(get_current_user)):
    """Live headcount per floor. Every logged-in role may see this."""
    return [{"floor": floor, "department": name, "employees": count}
            for floor, name, count in department_service.overview_rows()]


@router.get("")
def list_departments(user: CurrentUser = Depends(require_feature("departments"))):
    return [{"id": i, "code": code, "name": name, "floor": floor, "employees": count}
            for i, code, name, floor, count in department_service.department_summary()]


@router.post("", status_code=201)
def add_department(body: DepartmentIn,
                   user: CurrentUser = Depends(require_feature("departments"))):
    new_id = department_service.add_department(body.name, body.code, body.floor)
    return {"id": new_id}


@router.patch("/{dept_id}")
def update_department(dept_id: int, body: DepartmentUpdate,
                      user: CurrentUser = Depends(require_feature("departments"))):
    department_service.update_department(dept_id, body.name, body.floor)
    return {"message": "Department updated."}


@router.delete("/{dept_id}")
def delete_department(dept_id: int,
                      user: CurrentUser = Depends(require_feature("departments"))):
    department_service.delete_department(dept_id)
    return {"message": "Department deleted."}

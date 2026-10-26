from datetime import date
from typing import Optional

from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str
    password: str
    access_code: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class EmployeeIn(BaseModel):
    name: str
    designation: str
    field: Optional[str] = None
    salary: int
    date_of_joining: Optional[date] = None
    department_id: Optional[int] = None      


class EmployeeUpdate(BaseModel):
    """Send only what you want to change. `null` clears field / date_of_joining."""
    name: Optional[str] = None
    designation: Optional[str] = None
    field: Optional[str] = None
    salary: Optional[int] = None
    date_of_joining: Optional[date] = None


class TransferIn(BaseModel):
    department_id: int


class DepartmentIn(BaseModel):
    name: str
    code: str
    floor: int


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    floor: Optional[int] = None


class RoleIn(BaseModel):
    role: str

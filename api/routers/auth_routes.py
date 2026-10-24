from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import CurrentUser, get_current_user
from api.schemas import ChangePasswordIn, RegisterIn, TokenOut
from api.security import create_access_token
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn):
    """Create an account. The access code decides the role (admin / hr / it)."""
    role = auth_service.register_user(body.username, body.password, body.access_code)
    return TokenOut(access_token=create_access_token(body.username.strip()),
                    username=body.username.strip(), role=role)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Form fields `username` and `password`. (Swagger's green Authorize button uses this.)"""
    role = auth_service.authenticate(form.username, form.password)
    return TokenOut(access_token=create_access_token(form.username),
                    username=form.username, role=role)


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: CurrentUser = Depends(get_current_user)):
    auth_service.change_password(user.username, body.current_password, body.new_password)
    return {"message": "Password changed."}

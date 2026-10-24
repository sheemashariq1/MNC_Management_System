from fastapi import APIRouter, Depends

from api.deps import CurrentUser, require_feature
from api.schemas import RoleIn
from services import user_service

router = APIRouter(prefix="/users", tags=["Users (admin)"])


@router.get("")
def list_users(user: CurrentUser = Depends(require_feature("users"))):
    return [{"username": name, "role": role} for name, role in user_service.list_users()]


@router.patch("/{username}/role")
def change_role(username: str, body: RoleIn,
                user: CurrentUser = Depends(require_feature("users"))):
    user_service.change_role(username, body.role)
    return {"message": "Role updated."}


@router.delete("/{username}")
def delete_user(username: str, user: CurrentUser = Depends(require_feature("users"))):
    user_service.delete_user(username, acting_username=user.username)
    return {"message": "Account deleted."}

"""Dependencies: who is calling, and are they allowed?"""
from typing import NamedTuple

from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer

import session
from api.security import decode_token
from database import fetch

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class CurrentUser(NamedTuple):
    username: str
    role: str


def _load_role(username):
    rows = fetch("select role from users where username = %s", (username,))
    return rows[0][0] if rows else None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Check the token, load the user from the database, remember him for this request."""
    invalid = HTTPException(401, "Invalid or expired token.",
                            headers={"WWW-Authenticate": "Bearer"})
    username = decode_token(token)
    if username is None:
        raise invalid
    role = await run_in_threadpool(_load_role, username)    # fresh role from the database
    if role is None:                                        # account was deleted
        raise invalid
    # audit.log() reads the user from session, so set it for this request
    # (it is a ContextVar: other requests do not see it)
    session.login_user(username, role)
    return CurrentUser(username, role)


def require_feature(feature):
    """Use as:  Depends(require_feature("reports"))   -> 403 if the role may not."""
    async def checker(user: CurrentUser = Depends(get_current_user)):
        if not session.role_can(user.role, feature):
            raise HTTPException(403, "Your role is not allowed to do this.")
        return user
    return checker

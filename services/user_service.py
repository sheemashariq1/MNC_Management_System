"""Admin actions on accounts. No input() / print() in this file."""
import audit
import config
from database import run, fetch
from services import ServiceError


def list_users():
    return fetch("select username, role from users order by username")


def _admin_count():
    return fetch("select count(*) from users where role = 'admin'")[0][0]


def change_role(username, new_role):
    if new_role not in config.ROLES:
        raise ServiceError("Unknown role.")
    rows = fetch("select role from users where username = %s", (username,))
    if not rows:
        raise ServiceError("No such user.")
    old_role = rows[0][0]
    if old_role == "admin" and new_role != "admin" and _admin_count() <= 1:
        raise ServiceError("Cannot do that: this is the LAST admin account.")
    run("update users set role = %s where username = %s", (new_role, username))
    audit.log("ROLE_CHANGED", f"{username}: {old_role} -> {new_role}")


def delete_user(username, acting_username):
    if username == acting_username:
        raise ServiceError("You cannot delete the account you are logged in with.")
    rows = fetch("select role from users where username = %s", (username,))
    if not rows:
        raise ServiceError("No such user.")
    if rows[0][0] == "admin" and _admin_count() <= 1:
        raise ServiceError("Cannot do that: this is the LAST admin account.")
    run("delete from users where username = %s", (username,))
    audit.log("USER_DELETED", username)

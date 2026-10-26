"""Accounts and passwords"""
import hashlib
import hmac

import bcrypt

import audit
import config
from database import run, fetch
from services import ServiceError
from session import username

MIN_PASSWORD_LENGTH = 6
MAX_FAILED_ATTEMPTS = 5          # wrong passwords in a row ...
LOCK_MINUTES = 15                # ... lock the account for this long
MAX_PASSWORD_BYTES = 72          # bcrypt only uses the first 72 bytes


# ------------------------------------------------------------- hashing
def hash_password(password):
    """bcrypt hash as text (60 characters)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _legacy_hash(password, salt_hex):
    """The Step 2 hash, kept only so old accounts can still sign in once."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
    ).hex()


def verify_password(password, stored, salt):
    if salt is None:                              # bcrypt account
        try:
            return bcrypt.checkpw(password.encode(), stored.encode())
        except ValueError:                        # e.g. password longer than 72 bytes
            return False
    return hmac.compare_digest(_legacy_hash(password, salt), stored)


def role_for_code(code):
    """Which role does this access code belong to? (None if it matches nothing)"""
    found = None
    for role, secret in config.ACCESS_CODES.items():
        if hmac.compare_digest(code.encode(), secret.encode()):
            found = role
    return found


def check_password_rules(password):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ServiceError(f"Password is too short (min {MIN_PASSWORD_LENGTH} characters).")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ServiceError(f"Password is too long (max {MAX_PASSWORD_BYTES} bytes).")


# ------------------------------------------------------------ accounts------------------------------------------------------------------------
def signup_enabled():
    return bool(config.ACCESS_CODES)


def register_user(username, password, access_code):
    """Create an account. The access code decides the role. Returns the role."""
    if not signup_enabled():
        raise ServiceError("Sign up is disabled: no access codes are set in the .env file.")
    username = username.strip()
    if not 3 <= len(username) <= 20:
        raise ServiceError("User name must be 3-20 characters.")
    if fetch("select 1 from users where username = %s", (username,)):
        raise ServiceError("That user name is already taken.")
    role = role_for_code(access_code)
    if role is None:
        audit.log("SIGNUP_BAD_CODE", "wrong access code", username=username)
        raise ServiceError("Invalid access code.")
    check_password_rules(password)
    saved = run(
        "insert into users(username, pass_hash, salt, role) values (%s, %s, NULL, %s)",
        (username, hash_password(password), role),
    )
    if saved is None:
        raise ServiceError("Could not create the account.")
    audit.log("SIGN_UP", f"new account, role={role}", username=username, role=role)
    return role

def _recent_failures(username):
    """Failed logins of this user since his last successful login, in the lock window."""
    return fetch(
        "select count(*) from audit_log "
        "where action = 'LOGIN_FAILED' and username = %s "
        "and logged_at > now() - interval %s minute "
        "and audit_id > (select coalesce(max(audit_id), 0) from audit_log "
        "where action = 'LOGIN' and username = %s)",
        (username, LOCK_MINUTES, username))[0][0]

def authenticate(username, password):
    """Check username + password. Returns the role, or raises ServiceError."""
    if _recent_failures(username[:20]) >= MAX_FAILED_ATTEMPTS:
        audit.log("LOGIN_BLOCKED", "too many failed attempts", username=username[:20])
        raise ServiceError(f"Too many failed attempts. Try again in {LOCK_MINUTES} minutes.")
    rows = fetch("select pass_hash, salt, role from users where username = %s", (username,))
    if rows:
        stored, salt, role = rows[0]
        if verify_password(password, stored, salt):
            if salt is not None:      # old account -> upgrade to bcrypt now
                run("update users set pass_hash = %s, salt = NULL where username = %s",
                    (hash_password(password), username))
            audit.log("LOGIN", f"role={role}", username=username, role=role)
            return role
    audit.log("LOGIN_FAILED", "wrong username or password", username=username[:20] or "-")
    raise ServiceError("Wrong username or password.")


def change_password(username, current_password, new_password):
    rows = fetch("select pass_hash, salt, role from users where username = %s", (username,))
    if not rows:
        raise ServiceError("Account not found.")
    stored, salt, role = rows[0]
    if not verify_password(current_password, stored, salt):
        audit.log("PASSWORD_CHANGE_FAILED", "wrong current password",
                  username=username, role=role)
        raise ServiceError("Current password is wrong.")
    check_password_rules(new_password)
    run("update users set pass_hash = %s, salt = NULL where username = %s",
        (hash_password(new_password), username))
    audit.log("PASSWORD_CHANGED", username=username, role=role)

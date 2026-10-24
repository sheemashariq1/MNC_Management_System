import pytest

import config
import database
import session
from services import ServiceError, auth_service as auth


# ---------------------------------------------------------------- hashing
def test_hash_is_bcrypt_and_salted():
    h1, h2 = auth.hash_password("secret1"), auth.hash_password("secret1")
    assert h1.startswith("$2b$") and len(h1) == 60
    assert h1 != h2                    # random salt: same password, different hash


def test_verify_password():
    h = auth.hash_password("secret1")
    assert auth.verify_password("secret1", h, None)
    assert not auth.verify_password("wrong", h, None)


def test_verify_rejects_password_over_72_bytes():
    assert not auth.verify_password("a" * 80, auth.hash_password("secret1"), None)


# ---------------------------------------------------------------- sign up
def test_register_role_comes_from_access_code(codes):
    assert auth.register_user("hruser", "hrpass1", "HRC") == "hr"
    assert auth.register_user("ituser", "itpass1", "ITC") == "it"
    role, stored = database.fetch(
        "select role, pass_hash from users where username = 'hruser'")[0]
    assert role == "hr"
    assert "hrpass1" not in stored and stored.startswith("$2b$")   # never plain text


@pytest.mark.parametrize("username, password, code, message", [
    ("ab", "hrpass1", "HRC", "3-20"),
    ("x" * 21, "hrpass1", "HRC", "3-20"),
    ("hruser", "12345", "HRC", "too short"),
    ("hruser", "a" * 80, "HRC", "too long"),
    ("hruser", "hrpass1", "WRONG", "Invalid access code"),
])
def test_register_rejects_bad_input(codes, username, password, code, message):
    with pytest.raises(ServiceError, match=message):
        auth.register_user(username, password, code)
    assert database.fetch("select count(*) from users")[0][0] == 0


def test_register_rejects_duplicate_username(codes):
    auth.register_user("hruser", "hrpass1", "HRC")
    with pytest.raises(ServiceError, match="already taken"):
        auth.register_user("hruser", "otherpass", "ITC")


def test_register_disabled_without_access_codes(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_CODES", {})
    assert not auth.signup_enabled()
    with pytest.raises(ServiceError, match="disabled"):
        auth.register_user("hruser", "hrpass1", "x")


def test_bad_access_code_is_audited(codes, audit_entries):
    session.logout_user()                    # a stranger signing up is not logged in
    with pytest.raises(ServiceError):
        auth.register_user("intruder", "hrpass1", "WRONG")
    assert ("intruder", "-", "SIGNUP_BAD_CODE", "wrong access code") in audit_entries()


# ---------------------------------------------------------------- sign in
def test_authenticate_success_and_failures(codes, audit_entries):
    auth.register_user("hruser", "hrpass1", "HRC")
    assert auth.authenticate("hruser", "hrpass1") == "hr"
    with pytest.raises(ServiceError, match="Wrong username or password"):
        auth.authenticate("hruser", "nope")
    with pytest.raises(ServiceError, match="Wrong username or password"):
        auth.authenticate("ghost", "hrpass1")           # unknown user: same message
    actions = [a for _, _, a, _ in audit_entries()]
    assert actions.count("LOGIN") == 1 and actions.count("LOGIN_FAILED") == 2


def test_old_pbkdf2_account_is_upgraded_to_bcrypt():
    salt = "ab" * 16
    database.run("insert into users(username, pass_hash, salt, role) values (%s, %s, %s, 'admin')",
                 ("legacy", auth._legacy_hash("oldpass1", salt), salt))
    assert auth.authenticate("legacy", "oldpass1") == "admin"
    stored, salt_now = database.fetch("select pass_hash, salt from users where username = 'legacy'")[0]
    assert stored.startswith("$2b$") and salt_now is None      # converted
    assert auth.authenticate("legacy", "oldpass1") == "admin"  # still works afterwards


# ------------------------------------------------------- change password
def test_change_password(codes, audit_entries):
    auth.register_user("hruser", "hrpass1", "HRC")
    with pytest.raises(ServiceError, match="Current password is wrong"):
        auth.change_password("hruser", "wrong", "newpass1")
    auth.change_password("hruser", "hrpass1", "newpass1")
    with pytest.raises(ServiceError):
        auth.authenticate("hruser", "hrpass1")                 # old password is dead
    assert auth.authenticate("hruser", "newpass1") == "hr"
    actions = [a for _, _, a, _ in audit_entries()]
    assert "PASSWORD_CHANGED" in actions and "PASSWORD_CHANGE_FAILED" in actions


def test_change_password_enforces_rules(codes):
    auth.register_user("hruser", "hrpass1", "HRC")
    with pytest.raises(ServiceError, match="too short"):
        auth.change_password("hruser", "hrpass1", "123")

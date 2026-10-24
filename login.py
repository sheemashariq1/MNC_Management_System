"""Sign in / sign up / change password: the SCREEN part only.

The real work (hashing, rules, database, audit log) lives in
services/auth_service.py, so it can be tested without typing anything.
"""
import getpass

import schema  # noqa: F401  (makes sure `users` exists and is upgraded)
import session
from helpers import ask_int, ask_text
from services import ServiceError, auth_service

MAX_ATTEMPTS = 3


def _ask_new_password():
    """Ask until the rules pass and both typings match."""
    while True:
        password = getpass.getpass("create a password (min 6 characters): ")
        try:
            auth_service.check_password_rules(password)
        except ServiceError as err:
            print(err)
            continue
        if password == getpass.getpass("confirm password: "):
            return password
        print("Passwords do not match.")


def sign_up():
    if not auth_service.signup_enabled():
        print("Sign up is disabled: no access codes are set in the .env file.")
        return False
    username = ask_text("enter user name (3-20 characters): ", 20)
    code = getpass.getpass("enter your access code provided by the company: ")
    password = _ask_new_password()
    try:
        role = auth_service.register_user(username, password, code)
    except ServiceError as err:
        print(err)
        return False
    session.login_user(username, role)
    print(f"Account created. Now you can access (role: {role}).")
    return True


def sign_in():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        username = input("Enter username: ").strip()
        password = getpass.getpass("Enter password: ")
        try:
            role = auth_service.authenticate(username, password)
        except ServiceError:
            print(f"Wrong username or password ({MAX_ATTEMPTS - attempt} attempts left).")
            continue
        session.login_user(username, role)
        print(f"Now you can access (role: {role})")
        return True
    return False


def login1():
    """Returns True only if the user really signed in / signed up."""
    while True:
        print("1-sign in")
        print("2-sign up")
        print("3-exit")
        choice = ask_int("enter your choice: ", 1, 3)
        if choice == 1 and sign_in():
            return True
        if choice == 2 and sign_up():
            return True
        if choice == 3:
            return False


def change_password():
    current = getpass.getpass("enter your CURRENT password: ")
    new_password = _ask_new_password()
    try:
        auth_service.change_password(session.username(), current, new_password)
    except ServiceError as err:
        print(err)
        return
    print("PASSWORD CHANGED!")

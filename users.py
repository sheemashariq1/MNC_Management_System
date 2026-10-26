"""Admin-only: see accounts, change a user's role, delete a user."""

import config
import session
from helpers import ask_text, ask_int, ask_yes, print_rows
from services import ServiceError, user_service

def list_users():
    print_rows(["Username", "Role"], user_service.list_users())


def change_role():
    name = ask_text("enter username: ", 20)
    print("Roles:")
    for i, r in enumerate(config.ROLES, 1):
        print(f"{i}-{r}")
    new_role = config.ROLES[ask_int("pick the new role: ", 1, len(config.ROLES)) - 1]
    try:
        user_service.change_role(name, new_role)
    except ServiceError as err:
        print(err)
        return
    if name == session.username():
        session.login_user(name, new_role)     # session sync
    print("ROLE UPDATED!")


def delete_user():
    name = ask_text("enter username to delete: ", 20)
    if not ask_yes(f"Delete account '{name}'?"):
        return
    try:
        user_service.delete_user(name, session.username())
    except ServiceError as err:
        print(err)
        return
    print("ACCOUNT DELETED!")


def user_menu():
    if not session.require("users"):
        return
    while True:
        print("\n1-View all accounts")
        print("2-Change a user's role")
        print("3-Delete an account")
        print("4-Back")
        choice = ask_int("Enter your choice: ", 1, 4)
        if choice == 1:
            list_users()
        elif choice == 2:
            change_role()
        elif choice == 3:
            delete_user()
        else:
            break

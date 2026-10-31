import database
import schema  # noqa: F401  (creates / checks all tables)
import login
import audit
import reports
import session
import users
import administration as a
import employees as emp
from services import department_service
from helpers import ask_int, print_rows
from logger import get_logger
log = get_logger("main")

BANNER = """
==========================================================================
                      WELCOME TO MNC MANAGEMENT SYSTEM
                                  SKILLWAY
                                 IT COMPANY
                            SET UP IN GURGAON
                            HEADQUARTER - USA
==========================================================================
"""


def building_overview():
    print("====== AN OVERVIEW OF THE MNC BUILDING ======")
    # live numbers: counted from the employees table (JOIN + GROUP BY)
    print_rows(["FLOOR", "DEPARTMENT", "NO_OF_EMPLOYEES_WORKING"], department_service.overview_rows())


def run_menu(items, back_label):
    """Show only the options this user's role may use, then run the chosen one.

    items = list of (label, feature, function). The numbers are built
    automatically, so every role sees a clean 1, 2, 3... menu.
    """
    while True:
        allowed = [(label, func) for label, feature, func in items
                   if session.can(feature)]
        print()
        for i, (label, _) in enumerate(allowed, 1):
            print(f"{i}-{label}")
        print(f"{len(allowed) + 1}-{back_label}")
        choice = ask_int("Enter your choice: ", 1, len(allowed) + 1)
        if choice == len(allowed) + 1:
            return
        allowed[choice - 1][1]()


ADMIN_ITEMS = [
    ("HR DEPARTMENT", "hr", emp.hr),
    ("IT DEPARTMENT", "it", emp.it),
    ("OPERATION AND MAINTENANCE DEPARTMENT", "ops", a.md),
    ("CAFETERIA AND RECREATION HALL", "caf", a.cr),
    ("ALL EMPLOYEES (every department)", "all_employees", emp.all_employees),
    ("DEPARTMENTS (add / update / delete)", "departments", emp.department_menu),
    ("REPORTS (tables, charts, Excel)", "reports", reports.report_menu),
]


def administration_menu():
    run_menu(ADMIN_ITEMS, "BACK")


MAIN_ITEMS = [
    ("BUILDING OVERVIEW", "overview", building_overview),
    ("ADMINISTRATION", "administration", administration_menu),
    ("USER ACCOUNTS", "users", users.user_menu),
    ("AUDIT LOG", "audit", audit.audit_menu),
    ("CHANGE MY PASSWORD", "change_password", login.change_password),
]


def main():
    print(f"\nLogged in as: {session.username()}  (role: {session.role()})")
    run_menu(MAIN_ITEMS, "EXIT")
    audit.log("LOGOUT")
    print("###PROGRAM ENDED###")


if __name__ == "__main__":
    print(BANNER)
    print("*** You have to log in to access the system ***")
    try:
        if login.login1():
            main()
        else:
            print("Access denied.")
    except KeyboardInterrupt:
        print("\nBye!")
    except Exception:
        log.exception("unexpected crash")  
        print("Something went wrong. Details are saved in logs/mnc.log")
    finally:
        database.close()

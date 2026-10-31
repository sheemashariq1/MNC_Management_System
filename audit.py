"""Audit trail: WHO did WHAT and WHEN.

Every important action calls  audit.log("ACTION_NAME", "details").
The user and role come from the current session automatically.
Only admins can read the log (menu: AUDIT LOG).
"""
import session
from database import run, fetch
from helpers import ask_int, ask_text, ask_date, print_rows

AUDIT_HEADERS = ["Id", "When", "User", "Role", "Action", "Details"]
_SELECT = ("select audit_id, logged_at, username, role, action, details "
           "from audit_log")


def log(action, details="", username=None, role=None):
    """Write one line to the audit log.

    `username` / `role` are only needed when nobody is logged in yet
    (failed login, sign up, API calls).
    """
    who = (username or session.username() or "-")[:20]
    run(
        "insert into audit_log(username, role, action, details) values (%s, %s, %s, %s)",
        (who, (role or session.role() or "-")[:10], action[:30], str(details)[:255]),
    )

def _where(username, action):
    conditions, params = [], []
    if username:
        conditions.append("username = %s")
        params.append(username)
    if action:
        conditions.append("action like %s")
        params.append("%" + action.upper() + "%")
    where = " where " + " and ".join(conditions) if conditions else ""
    return where, params


def search(limit=50, username=None, action=None, offset=0):
    """Newest first. Optional: exact username and / or part of an action name."""
    where, params = _where(username, action)
    return fetch(_SELECT + where + " order by audit_id desc limit %s offset %s",
                 (*params, limit, offset))


def count(username=None, action=None):
    """How many entries match, ignoring limit and offset."""
    where, params = _where(username, action)
    return fetch("select count(*) from audit_log" + where, tuple(params))[0][0]

def _show(rows):
    # long details would wrap badly in the terminal, so cut them for display
    shown = [r[:5] + ((r[5] or "")[:70],) for r in rows]
    print_rows(AUDIT_HEADERS, shown)


def audit_menu():
    if not session.require("audit"):
        return
    while True:
        print("\n1-Latest entries")
        print("2-Entries of one user")
        print("3-Entries of one action type (e.g. EMP_UPDATED, LOGIN_FAILED)")
        print("4-Entries between two dates")
        print("5-Back")
        choice = ask_int("Enter your choice: ", 1, 5)
        if choice == 1:
            count = ask_int("how many latest entries (1-200)? ", 1, 200)
            _show(fetch(_SELECT + " order by audit_id desc limit %s", (count,)))
        elif choice == 2:
            name = ask_text("enter username: ", 20)
            _show(fetch(_SELECT + " where username = %s order by audit_id desc limit 200",
                        (name,)))
        elif choice == 3:
            word = ask_text("enter action name or part of it: ", 30).upper()
            _show(fetch(_SELECT + " where action like %s order by audit_id desc limit 200",
                        ("%" + word + "%",)))
        elif choice == 4:
            start = ask_date("enter FROM date ")
            end = ask_date("enter TO date ")
            _show(fetch(
                _SELECT + " where logged_at >= %s and logged_at < date_add(%s, interval 1 day) "
                          "order by audit_id desc limit 500", (start, end)))
        else:
            break

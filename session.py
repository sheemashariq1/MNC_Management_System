"""Who is logged in right now, and what are they allowed to do?

PERMISSIONS maps a feature name -> the set of roles allowed to use it.
Menus use can() to hide options, and the important functions use require()
as a second lock, so a feature stays protected even if a menu changes.
"""
from contextvars import ContextVar

PERMISSIONS = {
    "overview":        {"admin", "hr", "it"},
    "administration":  {"admin", "hr", "it"},
    "change_password": {"admin", "hr", "it"},
    "hr":              {"admin", "hr"},
    "it":              {"admin", "it"},
    "ops":             {"admin"},
    "caf":             {"admin"},
    "all_employees":   {"admin"},
    "departments":     {"admin"},
    "reports":         {"admin"},
    "users":           {"admin"},
    "audit":           {"admin"},
}

# One value PER request / thread of work (a ContextVar), not one global for everybody.
_current = ContextVar("current_user", default=(None, None))


def login_user(username, role):
    _current.set((username, role))


def logout_user():
    _current.set((None, None))


def username():
    return _current.get()[0]


def role():
    return _current.get()[1]


def role_can(user_role, feature):
    """True if THIS role may use this feature (works without a logged-in session)."""
    return user_role in PERMISSIONS.get(feature, set())


def can(feature):
    """True if the logged-in user's role may use this feature."""
    return role_can(role(), feature)

def require(feature):
    """Like can(), but prints a message when the answer is no."""
    if can(feature):
        return True
    print("ACCESS DENIED: your role does not allow this.")
    return False

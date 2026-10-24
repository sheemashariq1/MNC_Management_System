"""Business logic with NO input() and NO print().

The console menus, the tests and (Step 6) the FastAPI app all call these
functions. A broken rule (bad input, missing record, not allowed) raises
ServiceError, and its message is safe to show to the user.
"""


class ServiceError(Exception):
    """A rule was broken. str(error) is a friendly message."""

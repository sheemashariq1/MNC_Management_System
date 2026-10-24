"""Turn a ServiceError message into the right HTTP status code."""

# (text inside the message, status). The first match wins, so order matters.
_RULES = [
    ("too many failed", 429),
    ("wrong username or password", 401),
    ("invalid access code", 403),
    ("sign up is disabled", 403),
    ("no such", 404),
    ("does not exist", 404),
    ("not found", 404),
    ("last admin", 409),
    ("logged in with", 409),
    ("cannot delete", 409),
    ("already", 409),
]


def status_for(message):
    text = message.lower()
    for fragment, status in _RULES:
        if fragment in text:
            return status
    return 400

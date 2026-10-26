"""JWT login tokens."""
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT

import config

ALGORITHM = "HS256"


def _secret():
    if len(config.JWT_SECRET) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or too short (min 32 characters). Create one with:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "and put it in your .env file as JWT_SECRET=...")
    return config.JWT_SECRET


def check_secret():
    """Called at startup: stop the server right away if JWT_SECRET is missing."""
    _secret()


def create_access_token(username):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,                                                  # who
        "iat": now,                                                       # issued at
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),        # expires at
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token):
    """Returns the username, or None if the token is fake, changed or expired."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM],   # only HS256 allowed
                             options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload["sub"]

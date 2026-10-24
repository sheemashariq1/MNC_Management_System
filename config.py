"""Settings come from a `.env` file: never hard-coded, never committed to Git.

Copy `.env.example` to `.env` and fill in your own values.
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# read the .env that sits next to this file (works from any folder you run from)
load_dotenv(Path(__file__).with_name(".env"))

ROLES = ("admin", "hr", "it")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")   # empty -> we ask with getpass
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "MNC").strip()   # tests use MNC_test
if not re.fullmatch(r"[A-Za-z0-9_]+", MYSQL_DATABASE):
    raise ValueError("MYSQL_DATABASE may only contain letters, digits and _")
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# One sign-up access code per role. Whoever knows the HR code can only
# register as HR, and so on. Roles with no code set cannot be registered.
ACCESS_CODES = {}
for _role in ROLES:
    _code = os.getenv(_role.upper() + "_ACCESS_CODE", "").strip()
    if _code:
        ACCESS_CODES[_role] = _code

"""Shared test setup.

Tests use their OWN database (MNC_test). The real MNC database is never touched.
Before every test the tables are emptied, so tests cannot affect each other.
"""
import os
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so `import database` works
os.environ["MYSQL_DATABASE"] = "MNC_test"                      # BEFORE config is imported
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40          # fake secret, only for tests

import config  # noqa: E402

if not config.MYSQL_PASSWORD:
    pytest.exit("Put MYSQL_PASSWORD in your .env file: tests cannot ask for it.", returncode=2)

import database  # noqa: E402   (connects and creates MNC_test)
import schema    # noqa: E402
import session   # noqa: E402
from services import employee_service  # noqa: E402

TABLES = ["employees", "departments", "users", "audit_log", "SERVICES", "GAMES", "RESTAURANT"]


@pytest.fixture(autouse=True)
def clean_db():
    """Runs before EVERY test: empty tables, 5 starting departments, admin logged in."""
    assert config.MYSQL_DATABASE.endswith("_test"), "refusing to wipe a non-test database"
    cur = database.mycursor
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in TABLES:
        cur.execute(f"truncate table {table}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    database.mycon.commit()
    schema.create_tables()
    session.login_user("tester", "admin")
    yield
    session.logout_user()


@pytest.fixture
def depts():
    """{'HR': 2, 'IT': 3, ...}: department code -> dept_id"""
    return dict(database.fetch("select dept_code, dept_id from departments"))


@pytest.fixture
def hire(depts):
    """hire("Asha") adds an employee quickly and returns the new emp_id."""
    def _hire(name="Asha", dept="HR", salary=50000, designation="Manager",
              field=None, joined=date(2024, 8, 15)):
        return employee_service.add_employee(name, designation, field, salary,
                                             joined, depts[dept])
    return _hire


@pytest.fixture
def codes(monkeypatch):
    """Fixed sign-up access codes, so tests do not depend on your .env."""
    monkeypatch.setattr(config, "ACCESS_CODES", {"admin": "ADM", "hr": "HRC", "it": "ITC"})


@pytest.fixture
def audit_entries():
    """audit_entries() -> [(username, role, action, details), ...] oldest first"""
    def _read():
        return database.fetch(
            "select username, role, action, details from audit_log order by audit_id")
    return _read

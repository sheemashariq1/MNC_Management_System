import pytest

import session

ADMIN_ONLY = ["ops", "caf", "all_employees", "departments", "reports", "users", "audit"]


def test_admin_can_do_everything():
    session.login_user("a", "admin")
    assert all(session.can(f) for f in session.PERMISSIONS)


def test_hr_role():
    session.login_user("h", "hr")
    for allowed in ("overview", "administration", "change_password", "hr"):
        assert session.can(allowed)
    for denied in ["it"] + ADMIN_ONLY:
        assert not session.can(denied)


def test_it_role():
    session.login_user("i", "it")
    for allowed in ("overview", "administration", "change_password", "it"):
        assert session.can(allowed)
    for denied in ["hr"] + ADMIN_ONLY:
        assert not session.can(denied)


def test_nobody_logged_in_can_do_nothing():
    session.logout_user()
    assert not any(session.can(f) for f in session.PERMISSIONS)


def test_unknown_feature_and_unknown_role_are_denied():
    assert not session.can("launch_rockets")
    session.login_user("x", "intern")
    assert not session.can("overview")


@pytest.mark.parametrize("role, feature", [("hr", "audit"), ("it", "reports"), ("hr", "users")])
def test_require_prints_access_denied(capsys, role, feature):
    session.login_user("x", role)
    assert session.require(feature) is False
    assert "ACCESS DENIED" in capsys.readouterr().out


def test_protected_menus_refuse_a_wrong_role(capsys):
    """The second lock: even if a menu showed the option, the function itself says no."""
    import audit
    import employees
    import reports
    import users
    session.login_user("x", "hr")
    for protected in (audit.audit_menu, reports.report_menu, users.user_menu,
                      employees.it, employees.all_employees, employees.department_menu):
        protected()
    assert capsys.readouterr().out.count("ACCESS DENIED") == 6

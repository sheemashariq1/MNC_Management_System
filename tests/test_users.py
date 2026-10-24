import pytest

import database
from services import ServiceError, auth_service, user_service as users


@pytest.fixture
def accounts(codes):
    auth_service.register_user("boss", "bosspass1", "ADM")
    auth_service.register_user("hruser", "hrpass1", "HRC")


def test_list_users(accounts):
    assert users.list_users() == [("boss", "admin"), ("hruser", "hr")]


def test_change_role_and_audit(accounts, audit_entries):
    users.change_role("hruser", "it")
    assert dict(users.list_users())["hruser"] == "it"
    assert audit_entries()[-1][2:] == ("ROLE_CHANGED", "hruser: hr -> it")


def test_change_role_validation(accounts):
    with pytest.raises(ServiceError, match="Unknown role"):
        users.change_role("hruser", "superman")
    with pytest.raises(ServiceError, match="No such user"):
        users.change_role("ghost", "hr")


def test_last_admin_cannot_be_demoted_or_deleted(accounts):
    with pytest.raises(ServiceError, match="LAST admin"):
        users.change_role("boss", "hr")
    with pytest.raises(ServiceError, match="LAST admin"):
        users.delete_user("boss", acting_username="hruser")
    assert dict(users.list_users())["boss"] == "admin"


def test_second_admin_makes_demotion_possible(accounts):
    users.change_role("hruser", "admin")
    users.change_role("boss", "hr")                            # fine now: another admin exists
    assert dict(users.list_users()) == {"boss": "hr", "hruser": "admin"}


def test_delete_user(accounts, audit_entries):
    users.delete_user("hruser", acting_username="boss")
    assert [u for u, _ in users.list_users()] == ["boss"]
    assert audit_entries()[-1][2:] == ("USER_DELETED", "hruser")


def test_cannot_delete_yourself_or_missing_user(accounts):
    with pytest.raises(ServiceError, match="logged in with"):
        users.delete_user("boss", acting_username="boss")
    with pytest.raises(ServiceError, match="No such user"):
        users.delete_user("ghost", acting_username="boss")
    assert database.fetch("select count(*) from users")[0][0] == 2

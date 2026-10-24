import logging

import database


def test_run_returns_rowcount_and_fetch_returns_rows():
    assert database.run("insert into GAMES values (%s, %s)", (1, "Chess")) == 1
    assert database.fetch("select * from GAMES") == [(1, "Chess")]


def test_run_returns_none_and_logs_on_error(caplog):
    with caplog.at_level(logging.ERROR, logger="mnc"):
        assert database.run("insert into no_such_table values (1)") is None
    assert "query failed" in caplog.text


def test_values_are_not_written_to_the_log(caplog):
    with caplog.at_level(logging.ERROR, logger="mnc"):
        database.run("insert into no_such_table values (%s)", ("SuperSecret123",))
    assert "SuperSecret123" not in caplog.text


def test_duplicate_primary_key_is_rejected():
    database.run("insert into GAMES values (%s, %s)", (1, "Chess"))
    assert database.run("insert into GAMES values (%s, %s)", (1, "Carrom")) is None
    assert database.fetch("select count(*) from GAMES")[0][0] == 1

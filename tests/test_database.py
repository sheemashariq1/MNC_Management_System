import logging
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import mysql.connector as ms

import config
import database

ROOT = Path(__file__).resolve().parents[1]


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

def test_more_threads_than_connections_all_finish():
    # a separate process, because the pool size is fixed when database.py is imported
    script = textwrap.dedent("""
        import threading
        import database

        results, errors = [], []

        def work():
            try:
                results.append(database.fetch("select sleep(0.05), 1")[0][1])
            except Exception as err:
                errors.append(err)

        threads = [threading.Thread(target=work) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        print("finished", len(results), len(errors))
    """)
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True,
                            text=True, timeout=60, env={**os.environ, "MYSQL_POOL_SIZE": "2"})
    assert result.stdout.split()[-3:] == ["finished", "20", "0"], result.stderr


def test_connections_closed_by_the_server_are_replaced():
    database.fetch("select 1")
    killer = ms.connect(host=config.MYSQL_HOST, user=config.MYSQL_USER, password=config.MYSQL_PASSWORD)
    try:
        cursor = killer.cursor()
        cursor.execute("show processlist")
        pooled = [row[0] for row in cursor.fetchall() if row[3] == config.MYSQL_DATABASE]
        assert pooled
        for connection_id in pooled:
            cursor.execute(f"kill {int(connection_id)}")
    finally:
        killer.close()
    for _ in range(10):
        assert database.fetch("select 1") == [(1,)]
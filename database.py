"""Database access: a small connection pool and three helpers.

run()      runs an insert, update or delete and returns the number of rows changed
fetch()    runs a select and returns the rows
last_id()  returns the auto-increment id of this thread's latest insert

"""

import getpass
import sys
import threading
from contextlib import contextmanager

import mysql.connector as ms
from mysql.connector import pooling

import config
from logger import get_logger

log = get_logger("database")

# ask for the password when it is not in the .env file (typing stays hidden)
_password = config.MYSQL_PASSWORD or getpass.getpass("Enter your MySQL root password: ")

# the last inserted id, one per thread
_local = threading.local()

# The connector's pool raises an error when every connection is busy instead of waiting, so callers wait on this semaphore first.
_free = threading.BoundedSemaphore(config.MYSQL_POOL_SIZE)


def _create_pool():
    # the database may not exist yet, so create it on a plain connection first
    plain = ms.connect(host=config.MYSQL_HOST, user=config.MYSQL_USER, password=_password)
    try:
        cursor = plain.cursor()
        cursor.execute(f"create database if not exists `{config.MYSQL_DATABASE}`")
        cursor.close()
    finally:
        plain.close()
    return pooling.MySQLConnectionPool(
        pool_name="mnc",
        pool_size=config.MYSQL_POOL_SIZE,
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=_password,
        database=config.MYSQL_DATABASE,
        autocommit=True,
    )


try:
    _pool = _create_pool()
except ms.Error as err:
    log.error("could not connect to MySQL: %s", err)
    print("Could not connect to MySQL:", err)
    sys.exit(1)


@contextmanager
def connection():
    """Borrow a connection from the pool. It goes back when the block ends."""
    with _free:
        conn = _pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()


def run(query, params=()):
    """Run an insert, update or delete. Returns the rows changed, or None on error."""
    try:
        with connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                _local.last_id = cursor.lastrowid
                return cursor.rowcount
            finally:
                cursor.close()
    except ms.Error as err:
        # the values are left out of the log on purpose, they may be secrets
        log.error("query failed: %s | %s", err, query)
        print("Database error:", err)
        return None


def fetch(query, params=()):
    """Run a select and return all the rows."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()


def last_id():
    """The auto-increment id of this thread's latest run().

    Read it straight after your insert: audit.log() also calls run() and
    would replace it.
    """
    return getattr(_local, "last_id", None)


def close():
    """Close the pooled connections when the program ends."""
    _pool._remove_connections()  # the connector has no public method for this
"""Database connection + two small helpers used by every other file.

run()   -> for INSERT / UPDATE / DELETE / CREATE (commits, catches errors)
fetch() -> for SELECT (returns a list of rows)

Always pass values through `params` (the %s placeholders), never build the
query with .format() or + : that is what stops SQL injection.
"""
import getpass
import sys
import threading

import mysql.connector as ms

import config
from logger import get_logger

log = get_logger("database")

# password from the .env file; if it is not there, ask (typing stays hidden)
_password = config.MYSQL_PASSWORD or getpass.getpass("Enter your MySQL root password: ")

# The API handles several requests at the same time (threads) but we share ONE connection.
# The lock makes every statement run alone, so two requests can never mix up the cursor.
_lock = threading.RLock()
_local = threading.local()          # remembers the last inserted id PER thread


def _connect():
    """(Re)connect and select the database. Rebinds the module-level mycon / mycursor."""
    global mycon, mycursor
    mycon = ms.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=_password,
    )
    mycursor = mycon.cursor()
    mycursor.execute(f"create database if not exists `{config.MYSQL_DATABASE}`")
    mycursor.execute(f"use `{config.MYSQL_DATABASE}`")


try:
    _connect()
except ms.Error as err:
    log.error("could not connect to MySQL: %s", err)
    print("Could not connect to MySQL:", err)
    sys.exit(1)


def _execute(query, params):
    """Run one statement. If MySQL dropped an idle connection, reconnect once and retry."""
    try:
        mycursor.execute(query, params)
    except (ms.OperationalError, ms.InterfaceError):
        if mycon.is_connected():
            raise                       # a real error, not a lost connection
        log.warning("MySQL connection was lost: reconnecting")
        _connect()
        mycursor.execute(query, params)


def run(query, params=()):
    """Execute a write query. Returns affected row count, or None on error."""
    with _lock:
        try:
            _execute(query, params)
            mycon.commit()
            _local.last_id = mycursor.lastrowid
            return mycursor.rowcount
        except ms.Error as err:
            mycon.rollback()
            log.error("query failed: %s | %s", err, query)   # values are NOT logged (may be secrets)
            print("Database error:", err)
            return None


def fetch(query, params=()):
    """Execute a SELECT and return all rows."""
    with _lock:
        _execute(query, params)
        return mycursor.fetchall()


def last_id():
    """AUTO_INCREMENT id made by THIS thread's most recent run().

    Read it right after your insert and BEFORE anything else calls run()
    (audit.log() also calls run(), and would replace it).
    """
    return getattr(_local, "last_id", None)

"""All table definitions live here (one single place).
"""
from database import run, fetch

SEED_DEPARTMENTS = [
    # (code, name, floor)
    ("REC", "Reception and Lobby", 1),
    ("HR", "HR Department", 2),
    ("IT", "IT Department", 3),
    ("OPS", "Operation and Maintenance", 4),
    ("CAF", "Cafeteria and Recreation Hall", 5),
]


def _column_exists(table, column):
    return bool(fetch(
        "select 1 from information_schema.columns "
        "where table_schema = database() and table_name = %s and column_name = %s",
        (table, column)))


def upgrade_users_table():
    """Add the role column and widen pass_hash for bcrypt, on databases created before roles existed.

    Old accounts keep working: they become 'admin' and their password is
    converted to bcrypt automatically the next time they sign in.
    """
    if _column_exists("users", "role"):
        return
    run("alter table users add column role varchar(10) not null default 'admin'")
    run("alter table users alter column role drop default")
    run("alter table users modify pass_hash varchar(100) not null")
    run("alter table users modify salt char(32) null")


def create_tables():
    run(
        "create table if not exists departments("
        "dept_id int auto_increment primary key, "
        "dept_code varchar(10) not null unique, "
        "dept_name varchar(40) not null unique, "
        "floor int)"
    )
    run(
        "create table if not exists employees("
        "emp_id int auto_increment primary key, "
        "emp_name varchar(30) not null, "
        "designation varchar(25), "
        "field varchar(25), "
        "salary int, "
        "date_of_joining date, "
        "dept_id int not null, "
        "foreign key (dept_id) references departments(dept_id))"
    )
    # users: bcrypt hash (60 chars). `salt` is only filled for OLD pbkdf2
    # accounts that have not signed in since the upgrade (bcrypt keeps its salt inside the hash).
    run(
        "create table if not exists users("
        "username varchar(20) primary key, "
        "pass_hash varchar(100) not null, "
        "salt char(32) null, "
        "role varchar(10) not null)"
    )
    upgrade_users_table()
    run(
        "create table if not exists audit_log("
        "audit_id int auto_increment primary key, "
        "logged_at timestamp not null default current_timestamp, "
        "username varchar(20), "
        "role varchar(10), "
        "action varchar(30) not null, "
        "details varchar(255))"
    )
    run("create table if not exists SERVICES(Servicecode varchar(20) primary key,"
        "Service varchar(30) not null,Working_employees int)")
    run("create table if not exists GAMES(Gcode int primary key,"
        "Games_available varchar(30))")
    run("create table if not exists RESTAURANT(Rcode int primary key,"
        "Restaurant_available varchar(30),Couponcode varchar(10))")

    if not fetch("select 1 from departments limit 1"):
        for row in SEED_DEPARTMENTS:
            run("insert into departments(dept_code, dept_name, floor) "
                "values (%s, %s, %s)", row)


create_tables()

"""Generic menu engine for the small tables: SERVICES, GAMES, RESTAURANT."""

import audit
import schema  # noqa: F401  (makes sure the tables exist)
import session
from database import last_id, run, fetch
from helpers import ask_text, ask_int, ask_date, ask_yes, print_rows

# column order below MUST match the order used in schema.py
SERVICES = {
    "table": "SERVICES", "title": "OPERATION AND MAINTENANCE DEPARTMENT",
    "noun": "service", "pk": "Servicecode", "pk_label": "service code",
    "pk_kind": "text", "pk_auto": False, "pk_len": 20, "name": "Service",
    "columns": [
        ("Service", "type of service", "text", 30),
        ("Working_employees", "no. of employees working", "int", None),
    ],
}
GAMES = {
    "table": "GAMES", "title": "GAMES", "noun": "game",
    "pk": "Gcode", "pk_label": "game code", "pk_kind": "int", "pk_auto": False,
    "pk_len": None, "name": "Games_available",
    "columns": [("Games_available", "game name", "text", 30)],
}
RESTAURANT = {
    "table": "RESTAURANT", "title": "RESTAURANTS", "noun": "restaurant",
    "pk": "Rcode", "pk_label": "restaurant code", "pk_kind": "int",
    "pk_auto": False, "pk_len": None, "name": "Restaurant_available",
    "columns": [
        ("Restaurant_available", "restaurant name", "text", 30),
        ("Couponcode", "coupon code", "text", 10),
    ],
}


# --------------------------------------------------------------- helpers --------------------------------------------------------------
def _ask_value(label, kind, max_len=None):
    prompt = f"enter {label}: "
    if kind == "int":
        return ask_int(prompt, minimum=0)
    if kind == "date":
        return ask_date(prompt)
    return ask_text(prompt, max_len)


def _headers(cfg):
    return [cfg["pk"]] + [c[0] for c in cfg["columns"]]


def _select_sql(cfg):
    return f"select {', '.join(_headers(cfg))} from {cfg['table']}"


def _lookup(cfg, key):
    """All records whose id OR name equals `key`."""
    sel = _select_sql(cfg)
    if cfg["pk_kind"] == "int" and not key.isdecimal():
        return fetch(f"{sel} where {cfg['name']} = %s", (key,))
    if cfg["pk_kind"] == "int":
        return fetch(f"{sel} where {cfg['pk']} = %s or {cfg['name']} = %s",
                     (int(key), key))
    return fetch(f"{sel} where {cfg['pk']} = %s or {cfg['name']} = %s", (key, key))


def _find_one(cfg):
    """Ask for id or name and return exactly ONE record (or None)."""
    key = input(f"enter {cfg['pk_label']} or {cfg['noun']} name: ").strip()
    if not key:
        print("Nothing entered.")
        return None
    rows = _lookup(cfg, key)
    if not rows:
        print("No such record found")
        return None
    if len(rows) == 1:
        return rows[0]
    print("Several records match, please pick one by its id/code:")
    print_rows(_headers(cfg), rows)
    valid = {str(r[0]).lower(): r for r in rows}
    while True:
        chosen = input(f"enter the {cfg['pk_label']} to select: ").strip().lower()
        if chosen in valid:
            return valid[chosen]
        print("That is not one of the listed records.")


# ------------------------------------------------------------ operations --------------------------------------------------------------
def add_record(cfg):
    while True:
        names, values = [], []
        if not cfg["pk_auto"]:
            while True:
                code = _ask_value(cfg["pk_label"], cfg["pk_kind"], cfg["pk_len"])
                if fetch(f"select 1 from {cfg['table']} where {cfg['pk']} = %s",
                         (code,)):
                    print(f"That {cfg['pk_label']} already exists, try another.")
                else:
                    break
            names.append(cfg["pk"])
            values.append(code)
        for col, label, kind, max_len in cfg["columns"]:
            names.append(col)
            values.append(_ask_value(label, kind, max_len))
        marks = ", ".join(["%s"] * len(names))
        saved = run(
            f"insert into {cfg['table']} ({', '.join(names)}) values ({marks})",
            tuple(values),
        )
        if saved is not None:
            new_id = last_id()                # read before logging
            if cfg["pk_auto"]:
                print(f"ADDED! New {cfg['pk_label']} = {new_id}")
            else:
                print("ADDED!")
            audit.log(cfg["table"].upper() + "_ADDED", ", ".join(str(v) for v in values))
        if not ask_yes(f"do you want to add more {cfg['noun']}s?"):
            break


def remove_record(cfg):
    while True:
        row = _find_one(cfg)
        if row:
            print_rows(_headers(cfg), [row])
            if ask_yes("Are you sure you want to delete this record?"):
                run(f"delete from {cfg['table']} where {cfg['pk']} = %s", (row[0],))
                audit.log(cfg["table"].upper() + "_REMOVED", ", ".join(str(v) for v in row))
                print("RECORD DELETED!")
            else:
                print("Cancelled.")
        if not ask_yes(f"do you want to remove more {cfg['noun']}s?"):
            break


def display_all(cfg):
    print(f"---- {cfg['title']}: all records ----")
    rows = fetch(_select_sql(cfg) + f" order by {cfg['pk']}")
    print_rows(_headers(cfg), rows)


def update_record(cfg):
    while True:
        row = _find_one(cfg)
        if row:
            print_rows(_headers(cfg), [row])
            print("what do you want to update?")
            for i, (_, label, _, _) in enumerate(cfg["columns"], 1):
                print(f"{i}-{label}")
            pick = ask_int("enter your choice: ", 1, len(cfg["columns"]))
            col, label, kind, max_len = cfg["columns"][pick - 1]
            new_value = _ask_value("new " + label, kind, max_len)
            run(f"update {cfg['table']} set {col} = %s where {cfg['pk']} = %s",
                (new_value, row[0]))
            audit.log(cfg["table"].upper() + "_UPDATED",
                      f"{row[0]}: {label}: {row[pick]} -> {new_value}")
            print("UPDATED!")
        if not ask_yes(f"do you want to update more {cfg['noun']}s?"):
            break


def search_record(cfg):
    while True:
        key = input(f"enter {cfg['pk_label']} or {cfg['noun']} name: ").strip()
        rows = _lookup(cfg, key) if key else []
        if rows:
            print(f"{cfg['noun'].capitalize()} found!")
            print_rows(_headers(cfg), rows)
        else:
            print("No such record found")
        if not ask_yes(f"do you want to search for more {cfg['noun']}s?"):
            break


def crud_menu(cfg):
    noun = cfg["noun"]
    print(f"You can perform the following functions in {cfg['title']}")
    while True:
        print(f"\n1-Add new {noun}")
        print(f"2-Remove {noun}")
        print(f"3-Display all {noun}s")
        print(f"4-Update {noun} details")
        print(f"5-Search {noun}")
        print("6-Exit")
        choice = ask_int("Enter your choice: ", 1, 6)
        if choice == 1:
            add_record(cfg)
        elif choice == 2:
            remove_record(cfg)
        elif choice == 3:
            display_all(cfg)
        elif choice == 4:
            update_record(cfg)
        elif choice == 5:
            search_record(cfg)
        else:
            break


# ------------------------------------------- entry points used by MNC.py --------------------------------------------------------------------------------------------
def md():
    if session.require("ops"):
        crud_menu(SERVICES)


def cr():
    if not session.require("caf"):
        return
    print("You can perform the following functions in CAFETERIA AND RECREATION HALL")
    while True:
        print("\n1-Games available")
        print("2-Restaurant available")
        print("3-Exit")
        choice = ask_int("enter your choice: ", 1, 3)
        if choice == 1:
            crud_menu(GAMES)
        elif choice == 2:
            crud_menu(RESTAURANT)
        else:
            break

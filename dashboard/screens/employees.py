import datetime as dt

import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui

COLUMNS = ["id", "name", "designation", "field", "salary", "date_of_joining", "department"]


def _first_page():
    st.session_state["emp_page"] = 1


def show():
    is_admin = st.session_state["role"] == "admin"
    ui.page_header("Employees", "Everyone in the company." if is_admin
                   else "The people of your department.")
    ui.show_flash()
    # only admins may list departments; for hr / it the API already limits everything
    dept_ids = {d["name"]: d["id"] for d in api_client.departments()} if is_admin else {}

    left, right = st.columns([2, 1])
    search = left.text_input("Search by name or id", key="emp_search", on_change=_first_page)
    dept_id = None
    if is_admin:
        choice = right.selectbox("Department", ["All departments"] + list(dept_ids),
                                 key="emp_dept_filter", on_change=_first_page)
        dept_id = dept_ids.get(choice)

    page = st.session_state.get("emp_page", 1)
    size = st.session_state.get("emp_page_size", 25)
    rows, total = api_client.employees_page(search or None, dept_id, size, (page - 1) * size)
    pages = max(1, -(-total // size))
    if page > pages:
        # the page no longer exists, for example after the last person on it was terminated
        st.session_state["emp_page"] = pages
        st.rerun()

    if rows:
        df = ui.to_days(pd.DataFrame(rows, columns=COLUMNS), "date_of_joining")
        df["field"] = df["field"].fillna("-")
        st.dataframe(df, hide_index=True, width="stretch", height=ui.table_height(len(df)),
                     column_config={"id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                                    "name": st.column_config.TextColumn("Name", width="medium"),
                                    "designation": st.column_config.TextColumn("Designation", width="medium"),
                                    "field": "Field",
                                    "salary": ui.money("Salary"),
                                    "date_of_joining": ui.day("Joined"),
                                    "department": st.column_config.TextColumn("Department", width="large")})
    else:
        st.info("No employees found. Try another search, or hire someone below.")
    _pager(page, size, total, pages)

    _hire_form(is_admin, dept_ids)
    if rows:
        _manage(rows, is_admin, dept_ids)


def _pager(page, size, total, pages):
    first = (page - 1) * size + 1 if total else 0
    last = min(page * size, total)
    back, info, per_page, forward = st.columns([1, 3, 2, 1], vertical_alignment="bottom")
    if back.button("Previous", key="emp_prev", disabled=page <= 1):
        st.session_state["emp_page"] = page - 1
        st.rerun()
    info.caption(f"Showing {first}-{last} of {total} employees. Page {page} of {pages}.")
    per_page.selectbox("Rows per page", [10, 25, 50], index=1, key="emp_page_size",
                       on_change=_first_page)
    if forward.button("Next", key="emp_next", disabled=page >= pages):
        st.session_state["emp_page"] = page + 1
        st.rerun()


def _hire_form(is_admin, dept_ids):
    n = ui.nonce("hire_n")                      # new number after a success = empty form again
    with st.expander("Hire a new employee"):
        with st.form(f"hire_form_{n}"):
            name = st.text_input("Employee name", key=f"hire_name_{n}")
            designation = st.text_input("Designation", key=f"hire_designation_{n}")
            field = st.text_input("Field / specialisation (optional)", key=f"hire_field_{n}")
            salary = st.number_input("Salary", min_value=0, value=30000, step=1000,
                                     key=f"hire_salary_{n}")
            has_date = st.checkbox("Joining date known", value=True, key=f"hire_has_date_{n}")
            joined = st.date_input("Date of joining", value=dt.date.today(), key=f"hire_date_{n}")
            dept_name = (st.selectbox("Department", list(dept_ids), key=f"hire_dept_{n}")
                         if is_admin else None)
            submitted = st.form_submit_button("Hire", key=f"hire_submit_{n}")
        if submitted:
            payload = {"name": name, "designation": designation, "field": field.strip() or None,
                       "salary": int(salary),
                       "date_of_joining": joined.isoformat() if has_date else None,
                       "department_id": dept_ids.get(dept_name)}
            try:
                created = api_client.create_employee(payload)
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"Hired {created['name']} (id {created['id']}) into {created['department']}.")
                ui.bump("hire_n")
                st.rerun()


def _manage(rows, is_admin, dept_ids):
    st.subheader("Edit, transfer or terminate")
    labels = {f"{r['id']} - {r['name']} ({r['department']})": r for r in rows}
    emp = labels[st.selectbox("Choose an employee", list(labels), key="manage_pick")]
    names = ["Edit", "Transfer", "Terminate"] if is_admin else ["Edit", "Terminate"]
    tabs = dict(zip(names, st.tabs(names)))
    eid = emp["id"]

    with tabs["Edit"]:
        with st.form(f"edit_form_{eid}"):
            name = st.text_input("Employee name", value=emp["name"], key=f"edit_name_{eid}")
            designation = st.text_input("Designation", value=emp["designation"] or "",
                                        key=f"edit_designation_{eid}")
            field = st.text_input("Field / specialisation", value=emp["field"] or "",
                                  key=f"edit_field_{eid}")
            salary = st.number_input("Salary", min_value=0, value=int(emp["salary"] or 0),
                                     step=1000, key=f"edit_salary_{eid}")
            has_date = st.checkbox("Joining date known", value=bool(emp["date_of_joining"]),
                                   key=f"edit_has_date_{eid}")
            joined = st.date_input("Date of joining",
                                   value=ui.to_date(emp["date_of_joining"]) or dt.date.today(),
                                   key=f"edit_date_{eid}")
            submitted = st.form_submit_button("Save changes", key=f"edit_submit_{eid}")
        if submitted:
            wanted = {"name": name, "designation": designation, "field": field.strip() or None,
                      "salary": int(salary),
                      "date_of_joining": joined.isoformat() if has_date else None}
            changes = {k: v for k, v in wanted.items() if v != emp[k]}    # send only what changed
            if not changes:
                st.info("Nothing changed.")
            else:
                try:
                    api_client.update_employee(eid, changes)
                except ApiError as err:
                    st.error(err.message)
                else:
                    ui.flash(f"Updated {emp['name']}: " + ", ".join(changes) + ".")
                    st.rerun()

    if is_admin:
        with tabs["Transfer"]:
            others = [n for n in dept_ids if n != emp["department"]]
            target = st.selectbox("Move to department", others, key=f"transfer_to_{eid}")
            if st.button("Transfer", key=f"transfer_go_{eid}") and target:
                try:
                    api_client.transfer_employee(eid, dept_ids[target])
                except ApiError as err:
                    st.error(err.message)
                else:
                    ui.flash(f"{emp['name']} moved to {target}.")
                    st.rerun()

    with tabs["Terminate"]:
        st.warning(f"This removes {emp['name']} from the company records.")
        sure = st.checkbox("I am sure", key=f"term_sure_{eid}")
        if st.button("Terminate employee", disabled=not sure, key=f"term_go_{eid}"):
            try:
                api_client.terminate_employee(eid)
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"{emp['name']} was terminated.")
                st.rerun()

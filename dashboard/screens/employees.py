import datetime as dt

import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui

COLUMNS = ["id", "name", "designation", "field", "salary", "date_of_joining", "department"]


def show():
    st.header("Employees")
    ui.show_flash()
    is_admin = st.session_state["role"] == "admin"
    # only admins may list departments; for hr / it the API already limits everything
    dept_ids = {d["name"]: d["id"] for d in api_client.departments()} if is_admin else {}

    left, right = st.columns([2, 1])
    search = left.text_input("Search by name or id", key="emp_search")
    dept_id = None
    if is_admin:
        choice = right.selectbox("Department", ["All departments"] + list(dept_ids),
                                 key="emp_dept_filter")
        dept_id = dept_ids.get(choice)

    rows = api_client.employees(search or None, dept_id)
    if rows:
        st.dataframe(pd.DataFrame(rows, columns=COLUMNS), hide_index=True, width="stretch")
    else:
        st.info("No employees found.")
    st.caption(f"{len(rows)} employee(s)")

    _hire_form(is_admin, dept_ids)
    if rows:
        _manage(rows, is_admin, dept_ids)


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

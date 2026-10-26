import pandas as pd
import streamlit as st

import api_client
from api_client import ApiError
from screens import ui


def show():
    ui.page_header("Departments", "Add, rename or remove the departments of the company.")
    ui.show_flash()
    rows = api_client.departments()
    st.dataframe(pd.DataFrame(rows, columns=["id", "code", "name", "floor", "employees"]),
                 hide_index=True, width="stretch", height=ui.table_height(len(rows)),
                 column_config={"id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                                "code": "Code", "name": "Name",
                                "floor": st.column_config.NumberColumn("Floor", format="%d"),
                                "employees": st.column_config.NumberColumn("Employees", format="%d")})

    n = ui.nonce("dept_n")
    with st.expander("Add a department"):
        with st.form(f"dept_add_form_{n}"):
            name = st.text_input("Department name", key=f"dept_name_{n}")
            code = st.text_input("Short unique code (e.g. FIN)", key=f"dept_code_{n}")
            floor = st.number_input("Floor", min_value=0, value=1, step=1, key=f"dept_floor_{n}")
            submitted = st.form_submit_button("Add department", key=f"dept_add_submit_{n}")
        if submitted:
            try:
                api_client.add_department(name, code, int(floor))
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"Department {name.strip()} added.")
                ui.bump("dept_n")
                st.rerun()

    if not rows:
        return
    st.subheader("Edit or delete")
    labels = {f"{r['name']} ({r['code']}, {r['employees']} employees)": r for r in rows}
    dept = labels[st.selectbox("Choose a department", list(labels), key="dept_pick")]
    did = dept["id"]
    edit_tab, delete_tab = st.tabs(["Edit", "Delete"])

    with edit_tab:
        with st.form(f"dept_edit_form_{did}"):
            name = st.text_input("Name", value=dept["name"], key=f"dept_edit_name_{did}")
            floor = st.number_input("Floor", min_value=0, value=int(dept["floor"] or 0), step=1,
                                    key=f"dept_edit_floor_{did}")
            submitted = st.form_submit_button("Save changes", key=f"dept_edit_submit_{did}")
        if submitted:
            changes = {k: v for k, v in {"name": name, "floor": int(floor)}.items()
                       if v != dept[k]}
            if not changes:
                st.info("Nothing changed.")
            else:
                try:
                    api_client.update_department(did, changes)
                except ApiError as err:
                    st.error(err.message)
                else:
                    ui.flash(f"Department {dept['name']} updated.")
                    st.rerun()

    with delete_tab:
        st.warning("A department can only be deleted when nobody works there any more.")
        sure = st.checkbox("I am sure", key=f"dept_sure_{did}")
        if st.button("Delete department", disabled=not sure, key=f"dept_delete_{did}"):
            try:
                api_client.delete_department(did)
            except ApiError as err:
                st.error(err.message)
            else:
                ui.flash(f"Department {dept['name']} deleted.")
                st.rerun()

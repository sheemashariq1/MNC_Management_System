import schema  # creates departments + employees (and seeds departments)
from database import mycon, run, fetch


def table_exists(name):
    return bool(fetch(
        "select 1 from information_schema.tables "
        "where table_schema = database() and table_name = %s", (name,)))


def dept_id_for(code):
    return fetch("select dept_id from departments where dept_code = %s", (code,))[0][0]


def migrate():
    if fetch("select 1 from employees limit 1"):
        print("employees table already has data: nothing to migrate.")
        return

    moved = {"HR": 0, "IT": 0}

    if table_exists("HRdept"):
        hr_id = dept_id_for("HR")
        rows = fetch("select Empname, Designation, Salary, Date_of_joining "
                     "from HRdept order by Empid")
        for name, desig, salary, doj in rows:
            run("insert into employees(emp_name, designation, salary, date_of_joining, dept_id) "
                "values (%s, %s, %s, %s, %s)", (name, desig, salary, doj, hr_id))
            moved["HR"] += 1
    else:
        print("Old table HRdept not found: skipping HR.")

    if table_exists("ITdept"):
        it_id = dept_id_for("IT")
        rows = fetch("select Empname, Field, Designation, Salary from ITdept order by Empid")
        for name, field, desig, salary in rows:
            run("insert into employees(emp_name, field, designation, salary, dept_id) "
                "values (%s, %s, %s, %s, %s)", (name, field, desig, salary, it_id))
            moved["IT"] += 1
    else:
        print("Old table ITdept not found: skipping IT.")

    print(f"Migrated {moved['HR']} HR and {moved['IT']} IT employees.")
    print("Check them in the program, then (optional) remove the old tables with:")
    print("    DROP TABLE IF EXISTS HRdept, ITdept, BUILDING_OVERVIEW;")


if __name__ == "__main__":
    migrate()
    mycon.close()

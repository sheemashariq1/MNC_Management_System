"""Fills an EMPTY database with 14 sample employees (for screenshots and demos).

Run it once from the project folder:   python demo_data.py
If the database already has employees it does nothing, so it can never make duplicates.
The names and numbers are made up.
"""
import schema  # noqa: F401  (makes sure the tables and the 5 departments exist)
from database import mycon, run, fetch

# name, designation, field, salary, date of joining, department code
ROWS = [
    ("Ananya Sharma",  "HR Manager",          None,      85000,  "2021-04-12", "HR"),
    ("Rohan Mehta",    "Recruiter",           None,      48000,  "2023-07-03", "HR"),
    ("Priya Nair",     "HR Executive",        None,      42000,  "2024-02-19", "HR"),
    ("Arjun Verma",    "Engineering Manager", "Backend", 140000, "2020-01-15", "IT"),
    ("Sneha Iyer",     "Backend Developer",   "Python",  95000,  "2022-06-01", "IT"),
    ("Imran Ali",      "DevOps Engineer",     "Cloud",   105000, "2021-11-22", "IT"),
    ("Kavya Reddy",    "Data Analyst",        "AI/ML",   88000,  "2023-03-14", "IT"),
    ("Vikram Singh",   "QA Engineer",         "Testing", 62000,  "2024-08-05", "IT"),
    ("Meera Joshi",    "Frontend Developer",  "React",   78000,  "2022-09-12", "IT"),
    ("Suresh Yadav",   "Facility Supervisor", None,      38000,  "2019-05-20", "OPS"),
    ("Neha Gupta",     "Admin Executive",     None,      34000,  "2023-10-09", "OPS"),
    ("Raju Pandey",    "Head Chef",           "Food",    36000,  "2020-08-17", "CAF"),
    ("Farah Siddiqui", "Cafeteria Assistant", "Food",    26000,  "2024-01-08", "CAF"),
    ("Pooja Kapoor",   "Receptionist",        None,      30000,  "2022-12-01", "REC"),
]


def main():
    if fetch("select 1 from employees limit 1"):
        print("The database already has employees: nothing was added.")
        return
    dept_ids = dict(fetch("select dept_code, dept_id from departments"))
    for name, designation, field, salary, joined, code in ROWS:
        run("insert into employees(emp_name, designation, field, salary, date_of_joining, dept_id) "
            "values (%s, %s, %s, %s, %s, %s)",
            (name, designation, field, salary, joined, dept_ids[code]))
    print(f"Added {len(ROWS)} sample employees.")


if __name__ == "__main__":
    main()
    mycon.close()

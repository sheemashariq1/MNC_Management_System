"""Reports (pandas), charts (matplotlib) and exports (Excel / CSV).
Everything is saved inside a `reports/` folder next to this file.
Admin only (feature "reports").
"""

import webbrowser
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # draw straight into image files, no window needed
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

import audit
import session
from database import fetch
from services.employee_service import EMP_HEADERS, EMP_SQL
from helpers import ask_int, ask_yes, print_rows

REPORT_DIR = Path(__file__).with_name("reports")
SUMMARY_HEADERS = ["Department", "Employees", "Total salary", "Average salary",
                   "Median salary", "Highest salary", "Avg years of service"]


# ------------------------------------------------------------ load data -------------------------------------------------------------------------------
def load_employees():
    """All employees as a pandas DataFrame (a table in memory)."""
    rows = fetch(EMP_SQL + " order by e.emp_id")
    df = pd.DataFrame(rows, columns=EMP_HEADERS)
    df["Salary"] = pd.to_numeric(df["Salary"]).astype("Int64")   # whole numbers, blanks allowed
    df["Joined"] = pd.to_datetime(df["Joined"])                  # real dates, blanks = NaT
    return df


def _num(x):
    return 0 if pd.isna(x) else int(round(x))


def build_summary(df):
    """One row per department: count, total / average / median / highest salary, tenure."""
    depts = [r[0] for r in fetch("select dept_name from departments order by dept_id")]
    years = (pd.Timestamp.today().normalize() - df["Joined"]).dt.days / 365.25
    grouped = (
        df.assign(Years=years)
          .groupby("Department")
          .agg(Employees=("Emp_id", "count"), Total=("Salary", "sum"),
               Average=("Salary", "mean"), Median=("Salary", "median"),
               Highest=("Salary", "max"), Years=("Years", "mean"))
          .reindex(depts)                  # keep departments with 0 employees too
    )
    rows = []
    for dept, r in grouped.iterrows():
        rows.append([dept, _num(r["Employees"]), _num(r["Total"]), _num(r["Average"]),
                     _num(r["Median"]), _num(r["Highest"]),
                     None if pd.isna(r["Years"]) else round(float(r["Years"]), 1)])
    return pd.DataFrame(rows, columns=SUMMARY_HEADERS)


def _clean(df):
    """Blanks (NaN / NaT / NA) -> None so Excel and CSV show empty cells."""
    return df.astype(object).where(df.notna(), None)


# ---------------------------------------------------------------- charts ------------------------------------------------------------------------
def _save_chart(fig, name):
    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _bar_chart(labels, values, title, ylabel, color, whole_numbers=False):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, values, color=color)
    ax.bar_label(bars, padding=2)
    ax.set_title(title, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    if whole_numbers:                    
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    return fig


def chart_headcount(summary):
    fig = _bar_chart(summary["Department"], summary["Employees"],
                     "Employees per department", "Employees", "#2F6FDE", whole_numbers=True)
    return _save_chart(fig, "employees_per_department")


def chart_average_salary(summary):
    paid = summary[summary["Average salary"] > 0]
    if paid.empty:
        return None
    fig = _bar_chart(paid["Department"], paid["Average salary"],
                     "Average salary per department", "Salary", "#1E8E3E")
    return _save_chart(fig, "average_salary_per_department")


def chart_hires_per_year(df):
    years = df["Joined"].dt.year.dropna().astype(int)
    if years.empty:
        return None
    counts = years.value_counts().sort_index()
    counts = counts.reindex(range(counts.index.min(), counts.index.max() + 1), fill_value=0)
    fig = _bar_chart([str(y) for y in counts.index], counts.values,
                     "Employees hired per year", "Hired", "#E08A00", whole_numbers=True)
    return _save_chart(fig, "hires_per_year")


def charts_menu(df, summary):
    print("\n1-Employees per department")
    print("2-Average salary per department")
    print("3-Employees hired per year")
    print("4-All three")
    print("5-Back")
    choice = ask_int("Enter your choice: ", 1, 5)
    if choice == 5:
        return
    makers = {1: [lambda: chart_headcount(summary)],
              2: [lambda: chart_average_salary(summary)],
              3: [lambda: chart_hires_per_year(df)],
              4: [lambda: chart_headcount(summary),
                  lambda: chart_average_salary(summary),
                  lambda: chart_hires_per_year(df)]}[choice]
    paths = []
    for make in makers:
        path = make()
        if path is None:
            print("Not enough data for one of the charts (no salaries / joining dates yet).")
        else:
            paths.append(path)
            print("Chart saved:", path)
    if paths:
        audit.log("CHART_CREATED", ", ".join(p.name for p in paths))
        if ask_yes("open the chart(s) now?"):
            for p in paths:
                webbrowser.open(p.as_uri())


# --------------------------------------------------------------- exports ----------------------------------------------------------------------------
def _autowidth(sheet):
    for column in sheet.columns:
        longest = max(len(str(c.value)) if c.value is not None else 0 for c in column)
        sheet.column_dimensions[column[0].column_letter].width = min(longest + 2, 45)


def export_excel(df, summary):
    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / f"MNC_report_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    emp = df.assign(Joined=df["Joined"].dt.date)
    audit_rows = fetch("select audit_id, logged_at, username, role, action, details "
                       "from audit_log order by audit_id desc limit 1000")
    audit_df = pd.DataFrame(audit_rows, columns=audit.AUDIT_HEADERS)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _clean(emp).to_excel(writer, sheet_name="Employees", index=False)
        summary.to_excel(writer, sheet_name="Department summary", index=False)
        audit_df.to_excel(writer, sheet_name="Audit log", index=False)
        for sheet in writer.book.worksheets:
            _autowidth(sheet)
    print("Excel report saved:", path)
    audit.log("EXPORT_EXCEL", path.name)
    return path


def export_csv(df):
    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / f"employees_{datetime.now():%Y%m%d_%H%M%S}.csv"
    _clean(df.assign(Joined=df["Joined"].dt.date)).to_csv(path, index=False)
    print("CSV saved:", path)
    audit.log("EXPORT_CSV", path.name)
    return path


# ------------------------------------------------------------------ menu ------------------------------------------------------------------
def report_menu():
    if not session.require("reports"):
        return
    while True:
        print("\n1-Department-wise salary summary")
        print("2-Top 5 highest paid employees")
        print("3-Charts (saved as images)")
        print("4-Export everything to Excel")
        print("5-Export employees to CSV")
        print("6-Back")
        choice = ask_int("Enter your choice: ", 1, 6)
        if choice == 6:
            break
        df = load_employees()                 
        if df.empty:
            print("There are no employees yet, so there is nothing to report.")
            continue
        summary = build_summary(df)
        if choice == 1:
            rows = [[("-" if v is None or (isinstance(v, float) and pd.isna(v)) else v)
                     for v in row] for row in summary.itertuples(index=False)]
            print_rows(SUMMARY_HEADERS, rows)
        elif choice == 2:
            print_rows(EMP_HEADERS, fetch(EMP_SQL + " order by e.salary desc limit 5"))
        elif choice == 3:
            charts_menu(df, summary)
        elif choice == 4:
            export_excel(df, summary)
        else:
            export_csv(df)

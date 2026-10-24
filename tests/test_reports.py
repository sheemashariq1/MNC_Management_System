from datetime import date

import pandas as pd
import pytest

import reports


@pytest.fixture
def staffed(hire):
    hire("Asha", dept="HR", salary=50000, joined=date(2024, 8, 15))
    hire("Meera", dept="IT", salary=70000, joined=date(2025, 1, 10))
    hire("Imran", dept="IT", salary=90000, joined=date(2023, 3, 1))
    # a person with NO joining date, to prove blanks do not break the maths
    hire("Karan", dept="OPS", salary=30000, joined=None)


def test_load_employees_gives_proper_types(staffed):
    df = reports.load_employees()
    assert len(df) == 4
    assert str(df["Salary"].dtype) == "Int64"
    assert pd.api.types.is_datetime64_any_dtype(df["Joined"])
    assert df["Joined"].isna().sum() == 1


def test_summary_numbers(staffed):
    summary = reports.build_summary(reports.load_employees()).set_index("Department")
    it = summary.loc["IT Department"]
    assert (it["Employees"], it["Total salary"], it["Average salary"],
            it["Median salary"], it["Highest salary"]) == (2, 160000, 80000, 80000, 90000)
    assert summary.loc["HR Department", "Employees"] == 1


def test_summary_keeps_empty_departments_and_blank_years(staffed):
    summary = reports.build_summary(reports.load_employees()).set_index("Department")
    assert len(summary) == 5                                   # all departments, even empty ones
    assert summary.loc["Reception and Lobby", "Employees"] == 0
    assert pd.isna(summary.loc["Operation and Maintenance", "Avg years of service"])


def test_charts_are_saved_as_images(staffed, tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "REPORT_DIR", tmp_path)
    df = reports.load_employees()
    summary = reports.build_summary(df)
    for path in (reports.chart_headcount(summary), reports.chart_average_salary(summary),
                 reports.chart_hires_per_year(df)):
        assert path.exists() and path.suffix == ".png" and path.stat().st_size > 1000


def test_excel_export_has_three_sheets(staffed, tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "REPORT_DIR", tmp_path)
    df = reports.load_employees()
    reports.export_excel(df, reports.build_summary(df))
    book = pd.ExcelFile(next(tmp_path.glob("*.xlsx")))
    assert book.sheet_names == ["Employees", "Department summary", "Audit log"]
    assert len(pd.read_excel(book, sheet_name="Employees")) == 4


def test_csv_export_leaves_blanks_empty(staffed, tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "REPORT_DIR", tmp_path)
    reports.export_csv(reports.load_employees())
    text = next(tmp_path.glob("*.csv")).read_text()
    # Karan has no field and no joining date: both are EMPTY cells, not "<NA>" / "NaT"
    assert "4,Karan,Manager,,30000,,Operation and Maintenance" in text
    assert "<NA>" not in text and "NaT" not in text

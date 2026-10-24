from datetime import date

import pytest

import helpers


@pytest.fixture
def typed(monkeypatch):
    """typed("abc", "5") makes the next input() calls return 'abc', then '5'."""
    def _feed(*answers):
        it = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(it))
    return _feed


def test_ask_int_retries_until_valid(typed, capsys):
    typed("abc", "", "7")
    assert helpers.ask_int("n: ") == 7
    assert capsys.readouterr().out.count("whole number") == 2


def test_ask_int_limits(typed):
    typed("0", "11", "5")
    assert helpers.ask_int("n: ", minimum=1, maximum=10) == 5


def test_ask_text_rejects_empty_and_too_long(typed):
    typed("   ", "abcdef", "abc")
    assert helpers.ask_text("t: ", max_len=5) == "abc"


def test_ask_optional_returns_none_for_empty(typed):
    typed("")
    assert helpers.ask_optional("t: ") is None
    typed("Backend")
    assert helpers.ask_optional("t: ") == "Backend"


@pytest.mark.parametrize("typed_date", ["15-08-2024", "2024-08-15"])
def test_ask_date_accepts_both_formats(typed, typed_date):
    typed("31-31-2024", typed_date)                            # first one is invalid
    assert helpers.ask_date("d ") == date(2024, 8, 15)


@pytest.mark.parametrize("answer, expected", [("y", True), ("Y", True), ("n", False),
                                              ("", False), ("yes", False)])
def test_ask_yes(typed, answer, expected):
    typed(answer)
    assert helpers.ask_yes("ok?") is expected


def test_print_rows_empty(capsys):
    helpers.print_rows(["A"], [])
    assert "(no records)" in capsys.readouterr().out


def test_print_rows_aligns_columns_and_shows_blank_for_none(capsys):
    helpers.print_rows(["Id", "Name"], [(1, "Asha"), (22, None)])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Id  Name"
    assert lines[2] == "1   Asha"
    assert lines[3] == "22"                                    # None -> empty (and no trailing spaces)

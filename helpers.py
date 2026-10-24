"""Small reusable input helpers so the program never crashes on bad input."""
from datetime import datetime


def ask_text(prompt, max_len=None):
    """Non-empty text, optionally limited to max_len characters."""
    while True:
        value = input(prompt).strip()
        if not value:
            print("This field cannot be empty.")
        elif max_len and len(value) > max_len:
            print(f"Maximum {max_len} characters allowed.")
        else:
            return value


def ask_optional(prompt, max_len=None):
    """Text that may be left empty. Returns None if the user just presses Enter."""
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        if max_len and len(value) > max_len:
            print(f"Maximum {max_len} characters allowed.")
        else:
            return value


def ask_int(prompt, minimum=None, maximum=None):
    """Whole number within [minimum, maximum]."""
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
        elif maximum is not None and value > maximum:
            print(f"Value must be at most {maximum}.")
        else:
            return value


def ask_date(prompt):
    """Date as DD-MM-YYYY or YYYY-MM-DD. Returns a datetime.date."""
    while True:
        value = input(prompt + "(DD-MM-YYYY or YYYY-MM-DD): ").strip()
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        print("Invalid date.")


def ask_yes(prompt):
    """True only if the user types y / Y."""
    return input(prompt + " (y/n): ").strip().lower() == "y"


def print_rows(headers, rows):
    """Print rows as an aligned table."""
    if not rows:
        print("(no records)")
        return
    table = [[str(h) for h in headers]]
    table += [["" if c is None else str(c) for c in row] for row in rows]
    widths = [max(len(r[i]) for r in table) for i in range(len(headers))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    print(fmt.format(*table[0]).rstrip())
    print("  ".join("-" * w for w in widths))
    for row in table[1:]:
        print(fmt.format(*row).rstrip())

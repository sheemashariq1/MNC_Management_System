# Interview notes: MNC Management System

For your own preparation (you do not have to publish this file). Every answer is something this
project really does, so you can open the code and show it.

## The 60-second pitch
"It began as my Class 12 console project. I rebuilt it as a full-stack system: a FastAPI backend
with JWT login and role-based access, a Streamlit dashboard, a normalised MySQL schema, an audit
log, pandas reports, 163 tests with CI, and Docker. The main thing I learned is separating business
rules from screens, so the console, the API and the tests all use the same code."

## Questions you will probably get

**What is SQL injection and how did you stop it?**
If you build a query by pasting user text into it, input like `' OR '1'='1` becomes part of the SQL.
I send values separately with `%s` placeholders, so the database treats them as data only. The one
place I do put names into SQL (which column to update) comes from a whitelist, never from the user.
There are tests that try injection through names, search boxes and column names.

**Why bcrypt and not SHA-256?**
SHA-256 is fast, which is bad for passwords: an attacker can try billions of guesses. bcrypt is
deliberately slow and has a built-in random salt, so equal passwords give different hashes.

**How does your JWT login work?**
After login the server signs a token (username + expiry) with a secret. The client sends it on every
request; any change to it breaks the signature. I only accept HS256, so a token with `alg=none` is
refused. The token does not contain the role: I read the role from the database each request, so if
an admin changes a role or deletes an account it applies immediately.

**Why a services layer?**
Rules (validation, last-admin protection, audit) live in one place. The console, the API and the tests
call the same functions, so I test the rules once and cannot get two versions of them.

**How do you stop HR from seeing IT employees?**
Three layers: the menu hides options, each protected function checks the role again, and in the API
every employee endpoint is scoped to the caller's department (403 otherwise). Tests cover all three.

**Why a ContextVar for the current user?**
The API handles requests in parallel threads. A normal global would let request A see request B's
user, and the audit log would record the wrong person. A ContextVar has a separate value per request.
I also tested this with parallel requests from two different users.

**Your database connection is shared. Is that safe?**
Every statement runs under a lock, and the "last inserted id" is stored per thread. That is correct
for this scale (there is a test with 20 threads inserting at once). For real traffic I would use a
connection pool.

**What does the foreign key give you?**
The database itself refuses an employee with a non-existent department, and refuses to delete a
department that still has employees, even if my Python code had a bug. A test checks this at the SQL level.

**Explain your brute-force protection and its trade-off.**
5 failed logins since the last success lock that account for 15 minutes, counted from the audit log.
The trade-off: someone could lock a victim out on purpose. A real system would also rate-limit by IP.

**How do you test?**
pytest with a separate test database that is emptied before each test; API tests with FastAPI's
TestClient; the dashboard driven headlessly with Streamlit's AppTest; a concurrency test; and I
checked that tests really catch bugs by removing a security check and watching a test fail.

**Why Docker Compose?**
One command starts the database, API and dashboard together. The database has a healthcheck, so the
API waits until MySQL accepts logins. Secrets come from `.env` at run time and are never copied into
the image (`.dockerignore`).

**What would you improve next?**
Connection pooling, Alembic migrations, HTTPS plus refresh tokens, pagination, per-IP rate limiting.

## "Tell me about a bug you found" (real ones from this project)
- The original code put variables inside quotes (`'ename'`), so updates saved the literal text
  "newname" instead of the user's input.
- An update used `where salary = 50000`, which changed every employee with that salary.
- `lastrowid` was read after the audit insert, which had already replaced it; fixed by reading it first.
- A test in a clean virtual environment showed `streamlit` was missing from `requirements.txt`.

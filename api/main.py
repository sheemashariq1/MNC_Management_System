"""The API. Start it from the project folder with:

    python -m uvicorn api.main:app --reload

then open http://127.0.0.1:8000/docs  (interactive page where you can try every endpoint).
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

import schema  # noqa: F401  (makes sure the tables exist)
from api import security
from api.errors import status_for
from api.routers import (audit_routes, auth_routes, department_routes, employee_routes,
                         report_routes, user_routes)
from database import fetch
from logger import get_logger
from services import ServiceError

log = get_logger("api")

security.check_secret()          # fail fast: no JWT_SECRET -> the server does not start

app = FastAPI(
    title="MNC Management System API",
    version="1.0.0",
    description="Employees, departments, reports and audit log of the SKILLWAY MNC. "
                "Log in with POST /auth/login, then press Authorize.",
)

for module in (auth_routes, employee_routes, department_routes, user_routes,
               report_routes, audit_routes):
    app.include_router(module.router)


@app.exception_handler(ServiceError)
async def service_error_handler(request, exc):
    """Every broken business rule becomes a clean JSON error with the right status."""
    return JSONResponse(status_code=status_for(str(exc)), content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request, exc):
    log.exception("unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", include_in_schema=False)
def home():
    """The API has no web page of its own: send visitors to the interactive docs."""
    return RedirectResponse("/docs")

@app.get("/health", tags=["System"])
def health():
    """Is the server up and the database reachable?"""
    fetch("select 1")
    return {"status": "ok"}

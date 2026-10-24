# One image for everything: the API, the dashboard and the console app.
# docker-compose.yml starts it with a different command for each.
FROM python:3.12-slim

# no .pyc files, show logs immediately, matplotlib draws into files (no window)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

WORKDIR /app

# Install the libraries FIRST: Docker reuses this step (cache) until the lock file changes,
# so changing only your code does not reinstall everything.
COPY requirements.lock.txt .
RUN pip install -r requirements.lock.txt

# Now the code (see .dockerignore: .env, tests, logs ... are NOT copied in)
COPY . .

# Run as a normal user, not root
RUN useradd --create-home --uid 1000 app \
 && mkdir -p /app/logs /app/reports \
 && chown -R app:app /app
USER app

EXPOSE 8000 8501

# default = the API (docker-compose overrides this for the dashboard)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY requirements.txt install_dependencies.py ./

RUN python install_dependencies.py

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# COPY preserves local checkout modes, including 0600/0700 from umask 077.
# Normalize only image-owned runtime code, never host files or mounted secrets.
# Keep root ownership so the unprivileged app user can read but not modify code.
RUN chmod 0755 /app \
    && find /app/app /app/migrations -type d -exec chmod 0755 {} + \
    && find /app/app /app/migrations -type f -exec chmod 0644 {} + \
    && chmod 0644 /app/alembic.ini /app/requirements.txt /app/install_dependencies.py

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV XDG_CACHE_HOME=/tmp/cache XDG_CONFIG_HOME=/tmp/config
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN python -m pip install --no-cache-dir \
    playwright==1.63.0 fastapi==0.128.2 uvicorn==0.48.0 httpx==0.28.1

COPY backend/app ./app
RUN find /app -type d -exec chmod 0755 {} + \
    && find /app -type f -exec chmod 0644 {} +

RUN install -d -m 0700 -o pwuser -g pwuser /state \
    && touch /state/.initialized \
    && chown pwuser:pwuser /state/.initialized

USER pwuser
EXPOSE 8091
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health', timeout=3)" || exit 1
CMD ["python", "-m", "uvicorn", "app.providers.issuer_renderer.api:app", "--host", "0.0.0.0", "--port", "8091", "--no-access-log"]

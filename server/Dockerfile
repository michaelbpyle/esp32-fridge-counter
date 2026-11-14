# Hollygrove Community Fridge door counter: ingest + public read API.
# Build context is this folder (server/).  Not built or run on the dev PC
# (no Docker there); build it on the VM.  See README.md, section DEPLOY.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FRIDGE_DB_PATH=/data/fridge.db

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Non-root user; uid/gid 1000 so the bind-mounted data dir on the VM can be
# chowned to a normal number (chown -R 1000:1000 /opt/hollygrove/fridge/data).
RUN groupadd --gid 1000 fridge \
 && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin fridge \
 && mkdir /data && chown fridge:fridge /data
USER fridge
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/fridge/api/v1/health', timeout=4).status == 200 else 1)"]

# One worker on purpose: the rate limiter and query cache live in memory and
# SQLite has a single writer.  Access logging is done by the app (JSON lines).
CMD ["uvicorn", "app.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]

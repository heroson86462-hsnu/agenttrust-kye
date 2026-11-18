# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    KYE_DB_PATH=/data/kye_production.db

WORKDIR /app

# Create non-root runtime user and persistent volume mount point
RUN useradd -m -u 10001 kyeuser && mkdir -p /data && chown -R kyeuser:kyeuser /data /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

USER kyeuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["agenttrust-kye-server"]

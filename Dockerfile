# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY app/requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="hippo-hello-world" \
      org.opencontainers.image.description="Hello World Flask app" \
      org.opencontainers.image.source="https://github.com/mosavani/hippo_hello_world"

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ .

USER appuser

EXPOSE 8080

# gunicorn: 2 workers, bind on 0.0.0.0:8080, timeout 30s
CMD ["gunicorn", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]

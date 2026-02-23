"""
hippo_hello_world — Flask application with golden-signal Prometheus metrics.

Endpoints:
  GET /        → "Hello, World!"
  GET /health  → liveness probe
  GET /ready   → readiness probe
  GET /metrics → Prometheus scrape endpoint

Golden signals tracked:
  - Latency   : http_request_duration_seconds (histogram)
  - Traffic   : http_requests_total (counter)
  - Errors    : http_requests_total{status=~"5.."}
  - Saturation: process_resident_memory_bytes, process_cpu_seconds_total (built-in)
  - Uptime    : app_uptime_seconds (gauge)
"""

import os
import time
import threading
import random

from flask import Flask, jsonify, request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = Flask(__name__)

APP_START_TIME = time.time()

# ---------------------------------------------------------------------------
# Prometheus metrics — golden signals
# ---------------------------------------------------------------------------

# Traffic + Errors (labels allow slicing by method/endpoint/status)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"],
)

# Latency — histogram with SLO-friendly buckets (ms range expressed in seconds)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Saturation — in-flight requests (how 'full' the service is right now)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

# Uptime — seconds since process start
APP_UPTIME = Gauge(
    "app_uptime_seconds",
    "Seconds since the application started",
)

# Readiness state (0 = not ready, 1 = ready) — useful for saturation dashboards
APP_READY = Gauge(
    "app_ready",
    "Whether the application is ready to serve traffic (1=ready, 0=not ready)",
)

# ---------------------------------------------------------------------------
# Background thread: refresh uptime gauge every second
# ---------------------------------------------------------------------------
_ready = False  # flip to True after startup tasks complete


def _uptime_updater() -> None:
    while True:
        APP_UPTIME.set(time.time() - APP_START_TIME)
        time.sleep(1)


threading.Thread(target=_uptime_updater, daemon=True).start()

# ---------------------------------------------------------------------------
# Middleware: instrument every request automatically
# ---------------------------------------------------------------------------

@app.before_request
def _before() -> None:
    request._start_time = time.time()
    REQUESTS_IN_PROGRESS.labels(
        method=request.method,
        endpoint=request.path,
    ).inc()


@app.after_request
def _after(response):
    latency = time.time() - getattr(request, "_start_time", time.time())
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.path,
    ).observe(latency)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        http_status=str(response.status_code),
    ).inc()
    REQUESTS_IN_PROGRESS.labels(
        method=request.method,
        endpoint=request.path,
    ).dec()
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def hello():
    time.sleep(random.uniform(0.1, 0.9))  # simulate random latency
    return jsonify(message="Hello, World!"), 200


@app.route("/health")
def health():
    """Kubernetes liveness probe — returns 200 as long as the process is running."""
    return jsonify(status="ok", uptime_seconds=round(time.time() - APP_START_TIME, 2)), 200


@app.route("/ready")
def ready():
    """
    Kubernetes readiness probe — returns 200 when the app is ready to serve
    traffic, 503 during warm-up / controlled shut-down.
    """
    if _ready:
        APP_READY.set(1)
        return jsonify(status="ready"), 200
    APP_READY.set(0)
    return jsonify(status="not ready"), 503


@app.route("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    data = generate_latest(REGISTRY)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _startup() -> None:
    """Simulate a brief warm-up then mark the service as ready."""
    global _ready
    startup_delay = float(os.getenv("STARTUP_DELAY_SECONDS", "0"))
    if startup_delay:
        time.sleep(startup_delay)
    _ready = True
    APP_READY.set(1)


if __name__ == "__main__":
    threading.Thread(target=_startup, daemon=True).start()
    port = int(os.getenv("PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
else:
    # Running under gunicorn — mark ready immediately (gunicorn manages workers)
    _startup()

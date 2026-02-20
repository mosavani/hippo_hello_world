"""
Unit tests for hippo-hello-world Flask application.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../app"))

import pytest
from main import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestRootEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_hello_world(self, client):
        resp = client.get("/")
        data = resp.get_json()
        assert data["message"] == "Hello, World!"


class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_ok_status(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_includes_uptime(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestReadyEndpoint:
    def test_returns_ready_when_initialized(self, client):
        import main
        main._ready = True
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ready"

    def test_returns_503_when_not_ready(self, client):
        import main
        main._ready = False
        resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "not ready"
        main._ready = True


class TestMetricsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_content_type_is_prometheus(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.content_type

    def test_includes_request_counter(self, client):
        client.get("/")
        resp = client.get("/metrics")
        assert b"http_requests_total" in resp.data

    def test_includes_latency_histogram(self, client):
        client.get("/")
        resp = client.get("/metrics")
        assert b"http_request_duration_seconds" in resp.data

    def test_includes_uptime_gauge(self, client):
        resp = client.get("/metrics")
        assert b"app_uptime_seconds" in resp.data

    def test_includes_in_progress_gauge(self, client):
        resp = client.get("/metrics")
        assert b"http_requests_in_progress" in resp.data

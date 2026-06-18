import logging

from backend.main import app
from backend.shared.logging import RequestIdFilter, request_id_var
from fastapi.testclient import TestClient


def test_request_id_filter_injects_contextvar_value():
    token = request_id_var.set("abc123")
    try:
        record = logging.LogRecord("n", logging.INFO, "p", 1, "msg", None, None)
        RequestIdFilter().filter(record)
        assert record.request_id == "abc123"
    finally:
        request_id_var.reset(token)


def test_request_id_filter_defaults_to_dash_when_unset():
    record = logging.LogRecord("n", logging.INFO, "p", 1, "msg", None, None)
    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "-"


def test_health_response_has_request_id_header():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")  # present and non-empty


def test_provided_request_id_is_echoed_back():
    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-ID": "trace-xyz-123"})
    assert resp.headers.get("X-Request-ID") == "trace-xyz-123"

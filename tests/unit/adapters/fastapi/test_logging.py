import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from interface.api.middlewares.logging import LoggingMiddleware


def test_logging_middleware_logs_http_access_with_cloudflare_request_id(caplog):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping", name="ping_route")
    async def ping():
        return {"ok": True}

    client = TestClient(app)

    with caplog.at_level(
        logging.DEBUG, logger="interface.api.middlewares.logging"
    ):
        response = client.get(
            "/ping?limit=10",
            headers={
                "cf-ray": "cf-request-id",
                "cf-connecting-ip": "1.2.3.4",
                "cf-ipcountry": "TW",
                "user-agent": "pytest",
                "x-forwarded-for": "1.2.3.4",
                "x-forwarded-proto": "https",
            },
        )

    assert response.status_code == 200
    record = next(
        record for record in caplog.records if record.message == "HTTP access"
    )
    assert record.event == "http_access"
    assert record.request_id == "cf-request-id"
    assert record.request_id_source == "cf-ray"
    assert record.route_name == "ping_route"
    assert record.headers["cf-ray"] == "cf-request-id"
    assert record.headers["cf-connecting-ip"] == "1.2.3.4"
    assert record.headers["cf-ipcountry"] == "TW"
    assert record.headers["user-agent"] == "pytest"
    assert record.headers["x-forwarded-for"] == "1.2.3.4"
    assert record.headers["x-forwarded-proto"] == "https"
    assert record.query_summary == {"limit": "10"}
    assert record.status_code == 200
    assert record.client == {
        "ip": "1.2.3.4",
        "country": "TW",
        "forwarded_for": "1.2.3.4",
        "scheme": "https",
        "user_agent": "pytest",
    }


def test_logging_middleware_generates_request_id_when_cloudflare_header_missing(caplog):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.post("/echo", name="echo_route")
    async def echo(payload: dict):
        return payload

    client = TestClient(app)

    with caplog.at_level(
        logging.DEBUG, logger="interface.api.middlewares.logging"
    ):
        response = client.post("/echo", json={"content": "hello", "value": 1})

    assert response.status_code == 200
    record = next(
        record for record in caplog.records if record.message == "HTTP access"
    )
    assert record.event == "http_access"
    assert record.request_id.startswith("req_")
    assert record.request_id_source == "generated"
    assert record.route_name == "echo_route"
    assert record.input_summary == {
        "body_keys": ["content", "value"],
        "content_length": 5,
    }


def test_logging_middleware_sets_500_status_when_exception_bubbles(caplog):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/boom", name="boom_route")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(
        logging.DEBUG, logger="interface.api.middlewares.logging"
    ):
        response = client.get("/boom")

    assert response.status_code == 500
    record = next(
        record for record in caplog.records if record.message == "HTTP access"
    )
    assert record.event == "http_access"
    assert record.route_name == "boom_route"
    assert record.status_code == 500


def test_logging_middleware_skips_excluded_paths(caplog):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware, exclude_paths={"/metrics"})

    @app.get("/metrics", name="metrics_route")
    async def metrics():
        return {"ok": True}

    client = TestClient(app)

    with caplog.at_level(
        logging.DEBUG, logger="interface.api.middlewares.logging"
    ):
        response = client.get("/metrics")

    assert response.status_code == 200
    assert not any(record.message == "HTTP access" for record in caplog.records)

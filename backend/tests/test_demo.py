"""Demo endpoint tests: deterministic success and error simulation."""

from __future__ import annotations

import pytest

REALISTIC_500_ROUTES = [
    "/demo/error/undefined-name",
    "/demo/error/zero-division",
    "/demo/error/attr-error",
    "/demo/error/key-error",
]


def test_demo_success(client):
    response = client.get("/demo/success")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_error_400(client):
    response = client.get("/demo/error/400")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "HTTPException"


def test_demo_error_500(client):
    response = client.get("/demo/error/500")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["type"] == "RuntimeError"
    # Never leak internal details to clients.
    assert "Simulated internal server error" not in body["error"]["message"]


def test_demo_payment_timeout(client):
    response = client.get("/demo/error/payment-timeout")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["type"] == "PaymentProviderTimeout"


@pytest.mark.parametrize("route", REALISTIC_500_ROUTES)
def test_realistic_errors_return_500(client, route):
    response = client.get(route)
    assert response.status_code == 500
    # Clients get a generic message; the real detail stays in the server log.
    assert response.json()["error"]["message"] == "Internal server error"

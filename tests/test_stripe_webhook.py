
import hashlib
import hmac
import json
import os
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

TEST_DB = "./test_app.db"


def generate_signature(payload: str, secret: str, timestamp: int | None = None) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


@pytest.fixture(autouse=True)
def _env_and_db():
    os.environ["DATABASE_PATH"] = TEST_DB
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
    os.environ.pop("STRIPE_TOLERANCE_SECONDS", None)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    yield

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_webhook_valid_signature_stores_event(client: TestClient):
    payload = json.dumps(
        {
            "id": "evt_123",
            "object": "event",
            "type": "payment_intent.succeeded",
            "created": 1600000000,
            "data": {},
        }
    )
    sig = generate_signature(payload, "whsec_test_secret")

    r = client.post("/webhooks/provider", content=payload, headers={"Stripe-Signature": sig})
    assert r.status_code == 200
    assert r.json()["status"] == "received"

    with sqlite3.connect(TEST_DB) as conn:
        row = conn.execute("SELECT id, type FROM events WHERE id=?", ("evt_123",)).fetchone()
        assert row == ("evt_123", "payment_intent.succeeded")


def test_webhook_invalid_signature_returns_400(client: TestClient):
    payload = json.dumps({"id": "evt_bad", "object": "event", "type": "invoice.paid", "created": 1600000000})
    sig = generate_signature(payload, "whsec_WRONG_SECRET")

    r = client.post("/webhooks/provider", content=payload, headers={"Stripe-Signature": sig})
    assert r.status_code == 400
    assert "Invalid signature" in r.text


def test_webhook_missing_signature_returns_400(client: TestClient):
    payload = json.dumps({"id": "evt_missing_sig", "object": "event", "type": "invoice.paid", "created": 1600000000})
    r = client.post("/webhooks/provider", content=payload)
    assert r.status_code == 400


def test_webhook_replay_is_idempotent(client: TestClient):
    payload = json.dumps({"id": "evt_replay", "object": "event", "type": "charge.succeeded", "created": 1600000000})
    sig = generate_signature(payload, "whsec_test_secret")

    r1 = client.post("/webhooks/provider", content=payload, headers={"Stripe-Signature": sig})
    assert r1.status_code == 200

    r2 = client.post("/webhooks/provider", content=payload, headers={"Stripe-Signature": sig})
    assert r2.status_code == 200
    assert r2.json().get("idempotent_replay") is True

    with sqlite3.connect(TEST_DB) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events WHERE id=?", ("evt_replay",)).fetchone()[0]
        assert count == 1


def test_webhook_old_timestamp_returns_400(client: TestClient):
    payload = json.dumps({"id": "evt_old", "object": "event", "type": "invoice.paid", "created": 1600000000})
    old_ts = int(time.time()) - 600  # 10 minutes ago; default tolerance is 300
    sig = generate_signature(payload, "whsec_test_secret", timestamp=old_ts)

    r = client.post("/webhooks/provider", content=payload, headers={"Stripe-Signature": sig})
    assert r.status_code == 400

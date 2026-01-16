# Fintech Integration Lab

![CI](https://github.com/bentley-michael/fintech-integration-lab/actions/workflows/ci.yml/badge.svg)

A production-minded reference implementation of a webhook ingestion service built with **FastAPI**. Designed to demonstrate robust security practices for financial integrations without relying on vendor SDKs. Prevents double-processing (e.g., duplicate charges) when providers retry webhooks.

## Quick Demo (60 Seconds)

1. **Setup Environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[test]"
   ```

2. **Set Secret**
   ```powershell
   # Set the secret for the demo (PowerShell)
   $env:STRIPE_WEBHOOK_SECRET = "whsec_demo_secret_123"
   ```
   > **Note:** This environment variable must be set in **both** the server terminal and the client simulation terminal (or in a `.env` file).

3. **Run Server** (Keep this terminal open)
   ```powershell
   # The app will run at http://127.0.0.1:8000
   python -m uvicorn app.main:app --reload --port 8000
   ```

4. **Simulate Webhook** (In a new terminal)
   ```powershell
   .\.venv\Scripts\Activate.ps1
   $env:STRIPE_WEBHOOK_SECRET = "whsec_demo_secret_123"

   # Sends a correctly signed request to your local server.
   # Use --repeat 2 to demonstrate idempotency (second request detected as replay).
   python .\scripts\demo_send_webhook.py --repeat 2
   ```
   *Expected Output:*
   ```text
   [*] Generated Event ID: evt_d8cc... (Will reuse for all 2 attempts)
   [*] Signature Header: t=1737...,v1=...
   [*] Sending POST to http://127.0.0.1:8000/webhooks/provider (Repeat: 2)...
   [ATTEMPT] 1/2 -> Status: 200, Body: {"status": "received"}
   [ATTEMPT] 2/2 -> Status: 200, Body: {"status": "received", "idempotent_replay": true}
   [SUCCESS] First webhook accepted.
   ```

5. **Run Tests**
   ```powershell
   pytest
   ```

## Proof (Expected Behavior)

**Successful idempotency demo:**
```text
> python .\scripts\demo_send_webhook.py --repeat 2
[ATTEMPT] 1/2 -> Status: 200, Body: {"status": "received"}
[ATTEMPT] 2/2 -> Status: 200, Body: {"status": "received", "idempotent_replay": true}
```

**Failure example 1: Sender script missing secret**
```text
> python .\scripts\demo_send_webhook.py
[ERROR] Environment variable STRIPE_WEBHOOK_SECRET is missing.
Please set it in your terminal or .env file before running this script.
Example: $env:STRIPE_WEBHOOK_SECRET='whsec_...'
```

**Failure example 2: Server API missing secret (Misconfiguration)**
```text
> curl -X POST http://127.0.0.1:8000/webhooks/provider ...
HTTP/1.1 400 Bad Request
{"detail": "Server misconfigured: Missing STRIPE_WEBHOOK_SECRET"}
```

## How It Works

```text
[Stripe] --> (POST /webhooks/provider) --> [App]
                                            |
                                            +-- 1. Verify Signature (HMAC)
                                            +-- 2. Check Tolerance (Time)
                                            +-- 3. Idempotency Check (DB)
                                            |
                                            v
                                         [200 OK]
```

- **Signature Verification**: Manually parses `Stripe-Signature` (format: `t=TIMESTAMP,v1=SIGNATURE`) and computes HMAC-SHA256.
- **Replay Protection**: Rejects requests older than the configured tolerance (default 5 mins) to prevent replay attacks.
- **Timing Attack Resistance**: Uses `hmac.compare_digest` for constant-time string comparison.
- **Idempotency**: Enforces unique event processing at the database level (SQLite) using `event_id` as the primary key.
- **Deferred Processing**: (Recommended Pattern) Returns `200 OK` immediately after storage, allowing async workers to handle business logic.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_WEBHOOK_SECRET` | **Required** | The shared secret for HMAC signature verification. |
| `STRIPE_TOLERANCE_SECONDS` | `300` | Max age in seconds for a request to be considered valid (Data Freshness). |
| `DATABASE_PATH` | `./data/app.db` | File path for the SQLite database. |

### Environment Setup
- You can copy `.env.example` to `.env` to set these variables automatically.
- Alternatively, set them in PowerShell: `$env:STRIPE_WEBHOOK_SECRET = "..."`.

## Project Structure

```text
fintech-integration-lab/
├── app/
│   ├── webhooks/
│   │   └── provider.py    # Core signature verification & handler logic
│   ├── db.py              # SQLite wrapper enforcing idempotency
│   └── main.py            # FastAPI entrypoint
├── scripts/
│   └── demo_send_webhook.py  # Standalone script to spoof signed requests
├── tests/
│   └── test_stripe_webhook.py # Pytest suite (valid/invalid/replay cases)
└── README.md
```

## Security Notes / Threat Model

- **Authentication**: Usage of shared secret (HMAC-SHA256) ensures authenticity of the payload.
- **Integrity**: The signature covers `{timestamp}.{payload}`, preventing tamper attacks.
- **Freshness**: Timestamp checks mitigate replay attacks from valid but old captured requests.
- **Idempotency**: Database constraints prevent double-processing of financial transactions (e.g. duplicate charges).
- **Secret Management**: Keys are loaded via Environment Variables, never hardcoded in source.
- **HTTPS**: In a real production environment, this service must only accept traffic over TLS 1.2+.

---

*This project is for demonstration purposes. In production, run behind TLS (reverse proxy) and use a persistent DB (e.g., Postgres) plus a worker for async processing.*

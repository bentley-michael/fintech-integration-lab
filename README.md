# Fintech Integration Lab

Recruiter-ready FastAPI project demonstrating:
- Manual payment provider webhook verification (Stripe-style signature header) without external SDKs
- Replay protection via timestamp tolerance
- Idempotency via SQLite primary key constraint on event ID
- Local tests with pytest + FastAPI TestClient (no external services)

## Requirements
- Python 3.10+

## Setup (PowerShell)
```powershell
cd C:\Users\Nathan\ai_projects\fintech-integration-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[test]"

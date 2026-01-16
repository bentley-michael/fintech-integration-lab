import argparse
import hashlib
import hmac
import json
import time
import os
import sys
import uuid
import httpx
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configuration
DEFAULT_URL = "http://127.0.0.1:8000/webhooks/provider"

def generate_signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    mac = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"

def main():
    parser = argparse.ArgumentParser(description="Send signed webhook events to the fintech demo app.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to send the same request (to test idempotency)")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Webhook endpoint URL")
    args = parser.parse_args()

    # 1. Get Secret (Required)
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        print("[ERROR] Environment variable STRIPE_WEBHOOK_SECRET is missing.")
        print("Please set it in your terminal or .env file before running this script.")
        print("Example: $env:STRIPE_WEBHOOK_SECRET='whsec_...'")
        sys.exit(1)

    # 2. Create Payload (Generated ONCE to simulate replay/idempotency)
    event_id = f"evt_{uuid.uuid4()}"
    payload_dict = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "created": int(time.time()),
        "data": {
            "amount": 2000,
            "currency": "usd"
        }
    }
    payload_json = json.dumps(payload_dict)
    print(f"[*] Generated Event ID: {event_id} (Will reuse for all {args.repeat} attempts)")

    # 3. Sign Payload (Generated ONCE using the verified secret)
    signature = generate_signature(payload_json.encode('utf-8'), secret)
    print(f"[*] Signature Header: {signature}")

    # 4. Send Request(s)
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }
    
    first_attempt_success = False

    try:
        print(f"[*] Sending POST to {args.url} (Repeat: {args.repeat})...")
        
        for i in range(1, args.repeat + 1):
            response = httpx.post(args.url, data=payload_json, headers=headers)
            
            # Print condensed status in requested format
            print(f"[ATTEMPT] {i}/{args.repeat} -> Status: {response.status_code}, Body: {response.text}")
            
            # Capture success of the first attempt for exit code
            if i == 1:
                first_attempt_success = (response.status_code == 200)

        # 5. Exit Code Logic
        if first_attempt_success:
            print("[SUCCESS] First webhook accepted.")
            sys.exit(0)
        else:
            print("[FAILURE] First webhook rejected.")
            sys.exit(1)
            
    except httpx.ConnectError:
        print(f"[ERROR] Could not connect to {args.url}. Is the server running?")
        print("Try running: python -m uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

if __name__ == "__main__":
    main()

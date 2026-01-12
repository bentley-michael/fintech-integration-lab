import os
import time
import hmac
import hashlib
import logging
import json
from typing import Optional

from fastapi import APIRouter, Header, Request, HTTPException
from pydantic import ValidationError

from app.db import record_event
from app.models import ProviderEvent

router = APIRouter(prefix="/webhooks")
logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 300  # 5 minutes

def verify_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """
    Verifies the signature manually (HMAC-SHA256).
    Header format: t=timestamp,v1=signature,v1=signature,...
    1. Parse 't' and 'v1's.
    2. Check timestamp tolerance.
    3. Compute HMAC(secret, "{t}.{payload}").
    4. Constant-time compare against provided signatures.
    """
    if not sig_header:
        return False

    # 1. Parse Header
    # Split by ',' to get schemes
    # Example: t=161...,v1=sig1,v0=sig2
    items = sig_header.split(',')
    timestamp_str = None
    signatures = []

    for item in items:
        parts = item.split('=', 1)
        if len(parts) != 2:
            continue
        key, value = parts
        if key.strip() == 't':
            timestamp_str = value.strip()
        elif key.strip() == 'v1':
            signatures.append(value.strip())

    if not timestamp_str or not signatures:
        return False

    # 2. Check Tolerance
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False

    now = int(time.time())
    tolerance = int(os.getenv("STRIPE_TOLERANCE_SECONDS", DEFAULT_TOLERANCE))

    if abs(now - timestamp) > tolerance:
        logger.warning(f"Signature timestamp {timestamp} too old/new (now: {now}, tolerance: {tolerance})")
        return False

    # 3. Compute Expected Signature
    # Signed payload string: "{timestamp}.{raw_body}"
    to_sign = f"{timestamp}.".encode('utf-8') + payload
    
    try:
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            to_sign,
            hashlib.sha256
        ).hexdigest()
    except Exception as e:
        logger.error(f"HMAC computation failed: {e}")
        return False

    # 4. Compare
    # Check if ANY of the provided v1 signatures match
    for sig in signatures:
        if hmac.compare_digest(expected_sig, sig):
            return True

    return False


@router.post("/provider")
async def provider_webhook(request: Request, signature: Optional[str] = Header(default=None, alias="Stripe-Signature")):
    # Check configuration
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        # In production this might be a 500, but requirement says 400 with helpful message
        logger.error("Missing STRIPE_WEBHOOK_SECRET env var")
        raise HTTPException(status_code=400, detail="Server misconfigured: Missing STRIPE_WEBHOOK_SECRET")

    # Read Raw Body for verification
    try:
        body_bytes = await request.body()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read request body")

    # Verify
    if not signature:
        raise HTTPException(status_code=400, detail="Missing encoded Stripe-Signature header")

    valid = verify_signature(body_bytes, signature, webhook_secret)
    if not valid:
        logger.warning("Invalid provider signature verification")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Parse Payload
    try:
        payload = json.loads(body_bytes)
        event = ProviderEvent.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Payload parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON or schema")

    # Idempotency
    is_new = record_event(event.id, event.type, event.created)

    log_data = {
        "event_id": event.id,
        "type": event.type,
        "new": is_new,
        "action": "processed" if is_new else "skipped_idempotent"
    }
    logger.info(json.dumps(log_data))

    if not is_new:
        return {"status": "received", "idempotent_replay": True}

    return {"status": "received"}

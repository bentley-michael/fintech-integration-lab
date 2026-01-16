# Scripts

## demo_send_webhook.py

This script simulates a webhook provider (like Stripe) sending an event to your local server.
It handles the cryptographic signing so you can test the verification logic.

### Usage

1. Ensure the server is running:
   ```powershell
   uvicorn app.main:app
   ```

2. Run the script:
   ```powershell
   python scripts/demo_send_webhook.py
   ```

# Proof: Idempotency Replay

Command:
python .\scripts\demo_send_webhook.py --repeat 2

Expected output:
[ATTEMPT] 1/2 -> Status: 200, Body: {"status": "received"}
[ATTEMPT] 2/2 -> Status: 200, Body: {"status": "received", "idempotent_replay": true}

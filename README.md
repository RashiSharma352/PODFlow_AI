<<<<<<< HEAD
# PODFlow AI
A proof-of-delivery capture, review and billing handoff prototype for a road transport operator.

## Stack
- Streamlit role-specific UI
- FastAPI REST API
- SQLite database
- Pillow image validation and compression
- Optional Tesseract OCR (advisory text extraction only)

## Run
See [`deployment.md`](deployment.md) for the complete Windows setup, demo accounts, environment variables and deployment notes.

## Demo accounts
- Driver: `driver` / `driver123`
- Billing executive: `billing` / `billing123`

## Test
```bash
pytest -q
```

## Honest scope note
This is a prototype, not a production deployment. The current OCR is not a vision model; it does not verify signatures/stamps. Durable offline sync, GPS capture, SMS links and direct Tally integration are not implemented. Uploads are never automatically approved; a billing executive must review them.
=======
# PODFlow_AI
AI-powered Proof of Delivery Management System
>>>>>>> dcf8f5a3b52fa9ae74a2833e9339b2643ddf3b91

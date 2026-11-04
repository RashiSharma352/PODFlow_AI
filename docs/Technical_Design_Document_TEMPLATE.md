# PODFlow AI — Technical Design Document
**GitHub URL:** ADD PUBLIC REPOSITORY URL  
**Live app:** ADD DEPLOYED URL OR “Not deployed”

## Problem and scope
Capture POD images promptly, flag uncertain documents for human review, and prepare verified trips for billing.

## Assumptions
- Seeded trip records are fictional.
- CSV is a prototype Tally handoff, not a direct Tally integration.
- Driver and billing executive are the required roles.
- OCR is advisory; it never auto-approves a POD.
- SMS, customer portal and durable offline sync are not implemented in this starter.

## Architecture
Streamlit UI; FastAPI API; SQLite local database; Pillow image validation/compression; optional Tesseract OCR.

## Data model
`trips`: trip_id, client, vehicle, destination, freight, status, remarks, LR, e-way bill, branch, POD path, invoice status.

## Main flow
Driver selects trip and uploads image; API validates and compresses image; OCR extracts available text; uncertain record goes to review; billing executive reviews it; only verified trips are eligible for CSV export.

## AI failure handling
Missing OCR, unreadable text or LR mismatch are flagged. The source image remains authoritative. Reviewer must check stamp, signature, quantity, date and shortage/damage remarks. This version does not claim visual recognition of stamps/signatures.

## UI decisions
Restrained navy/white palette, role-specific navigation, visible status and reviewer notes, upload preview, trip register and billing CSV.

## Security and privacy
Demo credentials are not production-grade. Sample data is fictional. Production requires password hashing, secure session tokens, role checks on every API route, HTTPS, upload malware scanning, private object storage, retention controls, audit logs and DPDP review.

## Tests
Run `pytest`. The test ensures unavailable OCR does not auto-approve a document.

## Cut / next steps
Durable offline queue and retry; two-retake enforcement; verified GPS capture; vision model confidence thresholds; stronger role authorization; SMS link; client POD portal; branch cycle-time reporting; Tally mapping; PostgreSQL and production storage.

## Limitations
This is a starter prototype, not production-ready. OCR depends on image quality and Tesseract installation. Demo login is simple. The dashboard cannot calculate actual POD-to-invoice days without reliable timestamps.

# PODFlow AI — deployment and local run guide

## Status
This is a local demonstration prototype. It has not been deployed to a public hosting provider. No live URL is available yet.

## Requirements
- Python 3.11 or newer
- Windows 10/11, macOS or Linux
- Internet connection for initial Python package installation
- Tesseract OCR installed separately for OCR text extraction (optional; manual review still works without it)

## Run locally (Windows PowerShell)

1. Extract the project folder and open it in VS Code.
2. Open a terminal in the `PODFlow_AI` project root.
3. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

4. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again.

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. (Optional) Install Tesseract OCR for your operating system and ensure `tesseract.exe` is on PATH. The backend also checks the common Windows installation path `C:\Program Files\Tesseract-OCR\tesseract.exe`.

7. Start the API in Terminal 1:

   ```powershell
   uvicorn backend.main:app --reload
   ```

   API health check: `http://127.0.0.1:8000/health`
   Interactive API docs: `http://127.0.0.1:8000/docs`

8. Start the Streamlit UI in Terminal 2:

   ```powershell
   streamlit run frontend/app.py
   ```

9. Open the local URL printed by Streamlit (usually `http://localhost:8501`).

The SQLite database is created and seeded automatically on first API startup. POD images are stored under `uploads/`. Both are local development storage.

## Demo login details

| Role | Username | Password |
|---|---|---|
| Driver | `driver` | `driver123` |
| Billing executive | `billing` | `billing123` |

These are demonstration credentials only. Change them before any shared deployment.

## Environment variables

Set these in the environment where the relevant service runs. Names only are listed here; do not commit secret values.

| Variable | Purpose | Default |
|---|---|---|
| `PODFLOW_API_URL` | FastAPI base URL used by Streamlit | `http://127.0.0.1:8000` |
| `PODFLOW_SECRET_KEY` | HMAC signing key for demo bearer tokens | Development-only fallback; MUST be replaced |
| `PODFLOW_DRIVER_PASSWORD` | Driver demo password override | `driver123` |
| `PODFLOW_BILLING_PASSWORD` | Billing demo password override | `billing123` |
| `PODFLOW_DB_PATH` | Optional SQLite database file path | `podflow.db` in project root |

Example PowerShell configuration (use private values locally; never commit them):

```powershell
$env:PODFLOW_SECRET_KEY = "replace-with-a-long-random-secret"
$env:PODFLOW_DRIVER_PASSWORD = "set-a-private-driver-password"
$env:PODFLOW_BILLING_PASSWORD = "set-a-private-billing-password"
$env:PODFLOW_API_URL = "http://127.0.0.1:8000"
```

## Tests

From the project root, with the virtual environment activated:

```powershell
pytest -q
```

The current test suite covers seeded trip data, authentication, role restrictions, image compression, non-auto-approval, retake limits and billing export.

## Deployment outline

The prototype has not been deployed. For a hosted demonstration:
1. Deploy FastAPI as an HTTPS service.
2. Deploy Streamlit as a separate service.
3. Set `PODFLOW_API_URL` on the Streamlit service to the API's HTTPS base URL.
4. Set a strong `PODFLOW_SECRET_KEY` and private demo passwords in the hosting provider's secret manager.
5. Attach persistent storage for SQLite and uploaded images; ephemeral container disks are not suitable.
6. Restrict network access and configure HTTPS, backups, log redaction and retention.
7. Verify the deployed health endpoint, both role logins, upload/review flow and CSV download.

## Known limitations — read before review

- OCR uses optional Tesseract text extraction. It is not a trained vision AI model and does not reliably verify stamps, signatures, quantity, date or damage/shortage marks. The UI explicitly sends every upload to human review; OCR never approves a POD.
- Durable offline capture and background sync are not implemented. The current Streamlit upload requires network connectivity.
- SMS upload links for hired drivers are not implemented.
- GPS capture is not implemented; no GPS coordinates are claimed or stored.
- The CSV is a Tally-ready handoff template, not a direct Tally integration. POD filenames are included for manual attachment matching; invoice PDFs with embedded POD images are not generated.
- There is no external client portal, live GPS tracking, e-way bill provider integration or SMS gateway.
- SQLite and local image storage are prototype choices, not production infrastructure.
- Demo authentication uses HMAC-signed tokens and configurable demo passwords. Production requires individual accounts, password hashing, token expiry/revocation, audit logs, rate limiting and a formal access-control review.
- Cycle-time KPIs are not calculated because the supplied sample data does not contain reliable delivery and invoice timestamps.
- The seeded data is fictional and intended only for demonstration.

Do not present this prototype as production-ready. These limitations should be discussed honestly during the review.

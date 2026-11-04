from datetime import datetime, timezone
from pathlib import Path
import csv, hashlib, hmac, io, os, secrets, uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image, ImageOps
from .db import init, all_trips, one, update
from .verification import inspect_image

app = FastAPI(title="PODFlow AI API", version="1.0.0")
UPLOADS = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS.mkdir(exist_ok=True)
SECRET = os.getenv("PODFLOW_SECRET_KEY", "development-only-change-this-key")
DEMO_USERS = {
    "driver": (os.getenv("PODFLOW_DRIVER_PASSWORD", "driver123"), "driver"),
    "billing": (os.getenv("PODFLOW_BILLING_PASSWORD", "billing123"), "billing"),
}

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def make_token(username, role):
    payload = f"{username}:{role}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + ":" + sig

def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in required")
    token = authorization[7:]
    try:
        username, role, signature = token.split(":", 2)
    except ValueError:
        raise HTTPException(401, "Invalid session")
    expected = make_token(username, role).rsplit(":", 1)[1]
    if not hmac.compare_digest(signature, expected) or username not in DEMO_USERS or DEMO_USERS[username][1] != role:
        raise HTTPException(401, "Invalid session")
    return {"username": username, "role": role}

def require_role(role):
    def checker(user=Depends(current_user)):
        if user["role"] != role:
            raise HTTPException(403, f"{role} role required")
        return user
    return checker

@app.on_event("startup")
def startup():
    init()

@app.get("/health")
def health():
    return {"ok": True, "service": "PODFlow AI"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    key = username.strip().lower()
    item = DEMO_USERS.get(key)
    if not item or not hmac.compare_digest(password, item[0]):
        raise HTTPException(401, "Invalid demo credentials")
    return {"username": key, "role": item[1], "access_token": make_token(key, item[1]), "token_type": "bearer"}

@app.get("/trips")
def trips(user=Depends(current_user)):
    return all_trips()

@app.get("/trips/{trip_id}/pod-image")
def pod_image(trip_id: str, user=Depends(current_user)):
    trip = one(trip_id)
    if not trip or not trip.get("pod_path"):
        raise HTTPException(404, "POD image not found")
    path = (UPLOADS / Path(trip["pod_path"]).name).resolve()
    if path.parent != UPLOADS.resolve() or not path.is_file():
        raise HTTPException(404, "POD image not found")
    return FileResponse(path, media_type="image/jpeg", filename=path.name)

@app.post("/trips/{trip_id}/pod")
async def pod(trip_id: str, file: UploadFile = File(...), user=Depends(require_role("driver"))):
    t = one(trip_id)
    if not t:
        raise HTTPException(404, "Trip not found")
    raw = await file.read()
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "Empty or oversized image (maximum 10 MB)")
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception:
        raise HTTPException(400, "Upload a valid JPG, PNG or WEBP image")
    im.thumbnail((1400, 1400))
    path = UPLOADS / (trip_id + "_" + uuid.uuid4().hex[:8] + ".jpg")
    size = None
    for quality in (82, 74, 66, 58, 50, 42, 34, 26):
        im.save(path, "JPEG", quality=quality, optimize=True)
        size = path.stat().st_size
        if size <= 300 * 1024:
            break
    if size is None or size > 300 * 1024:
        path.unlink(missing_ok=True)
        raise HTTPException(413, "Could not compress image below 300 KB; use a smaller/clearer photo")
    result = inspect_image(str(path), t["lr"])
    update(trip_id, status="Needs review", remarks="; ".join(result["flags"])[:500],
           pod_path=path.name, invoice_status="Not ready", uploaded_at=now())
    return {"trip_id": trip_id, "size_bytes": size, "within_300_kb": size <= 300*1024, **result}

@app.post("/trips/{trip_id}/review")
def review(trip_id: str, decision: str = Form(...), remarks: str = Form(""),
           user=Depends(require_role("billing"))):
    t = one(trip_id)
    if not t:
        raise HTTPException(404, "Trip not found")
    if decision not in ["Verified", "Needs review", "Retake requested"]:
        raise HTTPException(400, "Invalid decision")
    count = int(t.get("retake_count") or 0)
    if decision == "Retake requested":
        if count >= 2:
            raise HTTPException(409, "Maximum of two retakes has been reached")
        count += 1
    verified_at = now() if decision == "Verified" else ""
    update(trip_id, status=decision, remarks=remarks[:500], retake_count=count,
           invoice_status="Ready" if decision == "Verified" else "Not ready",
           verified_at=verified_at)
    return {"trip_id": trip_id, "status": decision, "retake_count": count}

@app.get("/billing/export.csv")
def export_csv(user=Depends(require_role("billing"))):
    ready = [t for t in all_trips() if t["status"] == "Verified" and t["invoice_status"] != "Exported"]
    if not ready:
        raise HTTPException(404, "No verified trips awaiting export")
    output = io.StringIO()
    fields = ["trip_id", "client", "lr", "eway", "vehicle", "destination", "freight", "pod_path"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for t in ready:
        writer.writerow({k: t.get(k, "") for k in fields})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="podflow_tally_ready.csv"'})

@app.post("/trips/{trip_id}/export")
def mark_exported(trip_id: str, user=Depends(require_role("billing"))):
    t = one(trip_id)
    if not t:
        raise HTTPException(404, "Trip not found")
    if t["status"] != "Verified":
        raise HTTPException(409, "Only verified trips can be exported")
    update(trip_id, invoice_status="Exported", exported_at=now())
    return {"ok": True, "trip_id": trip_id, "invoice_status": "Exported"}

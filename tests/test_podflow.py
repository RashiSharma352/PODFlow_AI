import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend import db
from backend import main

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    main.UPLOADS.mkdir()
    db.init()
    return TestClient(main.app)

def token(client, username="driver", password="driver123"):
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}

def image_bytes():
    out = io.BytesIO()
    Image.new("RGB", (1200, 800), "white").save(out, format="JPEG")
    return out.getvalue()

def test_health_and_seed_data(client):
    assert client.get("/health").json()["ok"] is True
    trips = client.get("/trips", headers=token(client)).json()
    assert len(trips) >= 3
    assert any(t["trip_id"] == "TRP-66141" for t in trips)

def test_api_requires_login(client):
    assert client.get("/trips").status_code == 401

def test_driver_cannot_review(client):
    headers = token(client, "driver")
    response = client.post("/trips/TRP-66141/review",
        data={"decision":"Verified","remarks":"test"}, headers=headers)
    assert response.status_code == 403

def test_billing_can_review_and_verified_trip_becomes_exportable(client):
    headers = token(client, "billing", "billing123")
    response = client.post("/trips/TRP-66141/review",
        data={"decision":"Verified","remarks":"Stamp and signature checked"}, headers=headers)
    assert response.status_code == 200
    trip = db.one("TRP-66141")
    assert trip["status"] == "Verified"
    assert trip["invoice_status"] == "Ready"
    assert client.get("/billing/export.csv", headers=headers).status_code == 200

def test_driver_upload_is_compressed_and_never_auto_approved(client, monkeypatch):
    monkeypatch.setattr(main, "inspect_image", lambda path, lr: {
        "extracted_text":"", "ocr_available":False, "lr_match":None,
        "confidence":"low", "status":"Needs review",
        "flags":["OCR unavailable — manual review required"],
        "message":"POD received. Human review is required before billing."
    })
    headers = token(client)
    response = client.post("/trips/TRP-66152/pod",
        files={"file":("pod.jpg",image_bytes(),"image/jpeg")}, headers=headers)
    assert response.status_code == 200
    assert response.json()["size_bytes"] <= 300*1024
    assert response.json()["status"] == "Needs review"
    assert db.one("TRP-66152")["invoice_status"] == "Not ready"

def test_retake_limit_is_two(client):
    headers = token(client, "billing", "billing123")
    for expected_count in (1,2):
        response = client.post("/trips/TRP-66134/review",
            data={"decision":"Retake requested","remarks":"Please retake"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["retake_count"] == expected_count
    blocked = client.post("/trips/TRP-66134/review",
        data={"decision":"Retake requested","remarks":"Again"}, headers=headers)
    assert blocked.status_code == 409

def test_only_billing_can_export(client):
    assert client.get("/billing/export.csv", headers=token(client)).status_code == 403


def test_driver_can_submit_second_and_final_retake(client, monkeypatch):
    monkeypatch.setattr(main, "inspect_image", lambda path, lr: {
        "extracted_text":"", "ocr_available":False, "lr_match":None,
        "confidence":"low", "status":"Needs review",
        "flags":["OCR unavailable — manual review required"],
        "message":"POD received. Human review is required before billing."
    })
    billing = token(client, "billing", "billing123")
    driver = token(client, "driver")
    for expected_count in (1, 2):
        request = client.post("/trips/TRP-66134/review",
            data={"decision":"Retake requested","remarks":"Please retake"}, headers=billing)
        assert request.status_code == 200
        assert request.json()["retake_count"] == expected_count
        upload = client.post("/trips/TRP-66134/pod",
            files={"file":("retake.jpg",image_bytes(),"image/jpeg")}, headers=driver)
        assert upload.status_code == 200

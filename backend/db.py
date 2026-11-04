import os
import sqlite3
from pathlib import Path

DB = Path(os.getenv("PODFLOW_DB_PATH", Path(__file__).resolve().parent.parent / "podflow.db"))

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with connect() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY, client TEXT NOT NULL, vehicle TEXT NOT NULL,
            destination TEXT NOT NULL, freight INTEGER NOT NULL, status TEXT NOT NULL,
            remarks TEXT DEFAULT '', lr TEXT NOT NULL, eway TEXT NOT NULL,
            branch TEXT NOT NULL, pod_path TEXT DEFAULT '',
            invoice_status TEXT DEFAULT 'Not ready', retake_count INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT '', verified_at TEXT DEFAULT '',
            exported_at TEXT DEFAULT '', delivery_date TEXT DEFAULT ''
        )""")
        # Safe additive migration for databases created by the starter version.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(trips)")}
        additions = {
            "retake_count": "INTEGER DEFAULT 0",
            "uploaded_at": "TEXT DEFAULT ''",
            "verified_at": "TEXT DEFAULT ''",
            "exported_at": "TEXT DEFAULT ''",
            "delivery_date": "TEXT DEFAULT ''",
        }
        for name, definition in additions.items():
            if name not in cols:
                c.execute(f"ALTER TABLE trips ADD COLUMN {name} {definition}")
        if c.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 0:
            seed = [
              ("TRP-66120","Company B (cement)","MH20 EL 4521","Nagpur",38500,"Verified","None","LR-245678","EWB-66120","Chhatrapati Sambhajinagar","","Ready",0,"","","",""),
              ("TRP-66134","Company C (steel)","MH20 GT 7718","Pune",26000,"Retake requested","Stamp not visible","LR-66134","EWB-66134","Pune","","Not ready",0,"","","",""),
              ("TRP-66141","Company D (packaged foods)","MH17 BY 3092 (hired)","Indore",41200,"Needs review","Short by 6 cartons","LR-66141","EWB-66141","Indore","","Not ready",0,"","","",""),
              ("TRP-66152","Company B (cement)","MH20 EL 4521","Nashik",31800,"Missing POD","Awaiting upload","LR-66152","EWB-66152","Chhatrapati Sambhajinagar","","Not ready",0,"","","",""),
              ("TRP-66166","Company C (steel)","MH14 KL 2201","Mumbai",44200,"Missing POD","Awaiting upload","LR-66166","EWB-66166","Pune","","Not ready",0,"","","",""),
              ("TRP-66179","Company D (packaged foods)","MH17 BY 3092 (hired)","Bhopal",29400,"Needs review","Signature unclear","LR-66179","EWB-66179","Indore","","Not ready",0,"","","","")
            ]
            c.executemany("INSERT INTO trips (trip_id,client,vehicle,destination,freight,status,remarks,lr,eway,branch,pod_path,invoice_status,retake_count,uploaded_at,verified_at,exported_at,delivery_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", seed)

def all_trips():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM trips ORDER BY trip_id").fetchall()]

def one(trip_id):
    with connect() as c:
        row = c.execute("SELECT * FROM trips WHERE trip_id=?", (trip_id,)).fetchone()
        return dict(row) if row else None

def update(trip_id, **kw):
    allowed = {"status", "remarks", "pod_path", "invoice_status", "retake_count",
               "uploaded_at", "verified_at", "exported_at"}
    fields = {k:v for k,v in kw.items() if k in allowed}
    if not fields:
        return
    sql = ", ".join(k+"=?" for k in fields)
    with connect() as c:
        c.execute("UPDATE trips SET "+sql+" WHERE trip_id=?", list(fields.values())+[trip_id])

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = os.getenv("ROWE_DB_PATH", "roweauto.db")
FRONTEND_ORIGINS = [x.strip() for x in os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000"
).split(",") if x.strip()]

app = FastAPI(title="First Rowe Auto Intake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class Recommendation(BaseModel):
    work: str = ""
    estimate: str = ""
    urgency: Literal["Safety", "Soon", "Watch"] = "Soon"
    followUp: str = ""

class IntakeRequest(BaseModel):
    type: Literal["Repair", "Vehicle sale"]
    data: dict[str, Any]
    recommendations: list[Recommendation] = Field(default_factory=list)

def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db() -> None:
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS intakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intake_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                vehicle_year TEXT,
                vehicle_make TEXT,
                vehicle_model TEXT,
                mileage TEXT,
                vin TEXT,
                customer_decision TEXT,
                payload_json TEXT NOT NULL
            )
        """)

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

def require(data: dict[str, Any], fields: list[str]) -> None:
    missing = [f for f in fields if not str(data.get(f, "")).strip()]
    if missing:
        raise HTTPException(422, detail={"missing_fields": missing})

@app.post("/api/intakes", status_code=201)
def create_intake(body: IntakeRequest) -> dict[str, Any]:
    d = body.data

    if body.type == "Repair":
        require(d, ["name", "phone", "email", "referral", "year", "make", "model", "mileage", "vin", "concern"])
        vin = str(d.get("vin", "")).strip().upper()
        if len(vin) != 17:
            raise HTTPException(422, detail={"vin": "VIN must be 17 characters"})
    else:
        require(d, ["name", "phone", "email", "desiredVehicle"])

    created_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "type": body.type,
        "data": d,
        "recommendations": [r.model_dump() for r in body.recommendations],
    }

    with connect() as db:
        cur = db.execute(
            """INSERT INTO intakes
            (intake_type, created_at, customer_name, phone, email, vehicle_year,
             vehicle_make, vehicle_model, mileage, vin, customer_decision, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body.type, created_at, str(d.get("name", "")).strip(),
                str(d.get("phone", "")).strip(), str(d.get("email", "")).strip(),
                str(d.get("year", "")).strip() or None,
                str(d.get("make", "")).strip() or None,
                str(d.get("model", "")).strip() or None,
                str(d.get("mileage", "")).strip() or None,
                str(d.get("vin", "")).strip().upper() or None,
                str(d.get("decision", "")).strip() or None,
                json.dumps(payload, separators=(",", ":")),
            ),
        )
        intake_id = cur.lastrowid

    return {"id": intake_id, "created_at": created_at, "type": body.type}

@app.get("/api/intakes")
def list_intakes(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    with connect() as db:
        rows = db.execute(
            """SELECT id, intake_type, created_at, customer_name, phone, email,
                      vehicle_year, vehicle_make, vehicle_model, mileage, vin, customer_decision
               FROM intakes ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}

@app.get("/api/intakes/{intake_id}")
def get_intake(intake_id: int) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT payload_json, id, created_at FROM intakes WHERE id = ?", (intake_id,)).fetchone()
    if not row:
        raise HTTPException(404, detail="Intake not found")
    payload = json.loads(row["payload_json"])
    payload["id"] = row["id"]
    payload["created_at"] = row["created_at"]
    return payload

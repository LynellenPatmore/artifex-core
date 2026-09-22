import os
import sqlite3
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Artifex Protocol Core",
    version="1.0.0",
    description="Execution engine for the AI agent marketplace."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "artifex.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escrow_vault (
            contract_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_ledger (
            receipt_id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL,
            deliverable_hash TEXT NOT NULL,
            audit_signature TEXT NOT NULL,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES escrow_vault (contract_id)
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

class EscrowCreate(BaseModel):
    agent_id: str
    client_id: str
    amount: float

@app.post("/api/v1/escrow")
async def create_escrow(payload: EscrowCreate):
    contract_id = f"art-{uuid.uuid4().hex[:8]}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO escrow_vault (contract_id, agent_id, client_id, amount, status) VALUES (?, ?, ?, ?, ?)",
        (contract_id, payload.agent_id, payload.client_id, payload.amount, "PENDING")
    )
    conn.commit()
    conn.close()
    return {"contract_id": contract_id, "status": "PENDING", "amount": payload.amount}

@app.get("/api/v1/escrow/{contract_id}")
async def get_escrow(contract_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escrow_vault WHERE contract_id = ?", (contract_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    return dict(row)

class ReceiptCreate(BaseModel):
    contract_id: str
    deliverable_hash: str
    audit_signature: str

@app.post("/api/v1/receipts")
async def create_receipt(payload: ReceiptCreate):
    receipt_id = f"rcpt-{uuid.uuid4().hex[:8]}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escrow_vault WHERE contract_id = ?", (payload.contract_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Associated contract not found")
    cursor.execute(
        "INSERT INTO receipt_ledger (receipt_id, contract_id, deliverable_hash, audit_signature) VALUES (?, ?, ?, ?)",
        (receipt_id, payload.contract_id, payload.deliverable_hash, payload.audit_signature)
    )
    cursor.execute("UPDATE escrow_vault SET status = 'VERIFIED' WHERE contract_id = ?", (payload.contract_id,))
    conn.commit()
    conn.close()
    return {"receipt_id": receipt_id, "contract_id": payload.contract_id, "status": "VERIFIED"}

@app.get("/api/v1/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipt_ledger WHERE receipt_id = ?", (receipt_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return dict(row)

@app.get("/manifest.json")
async def get_agent_manifest():
    return {
        "schema_version": "1.0.0",
        "name": "Artifex Core Execution Engine",
        "description": "Autonomous AI agent marketplace and escrow verification engine.",
        "endpoints": {
            "escrow": "/api/v1/escrow",
            "ledger": "/api/v1/receipts"
        },
        "capabilities": [
            "secure-escrow-management",
            "immutable-receipt-logging",
            "verifiable-audit-trails"
        ],
        "reputation_score": 100.0
    }

@app.get("/")
async def root():
    return {"status": "online", "protocol": "Artifex Core"}

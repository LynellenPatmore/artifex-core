import os
import sqlite3
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Artifex Core", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MASTER_API_KEY = os.getenv("MASTER_API_KEY", "artifex-master-secret-999")
DB_FILE = "artifex.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escrow_vault (
            contract_id TEXT PRIMARY KEY,
            client_email TEXT,
            agent_id TEXT,
            amount REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_ledger (
            receipt_id TEXT PRIMARY KEY,
            contract_id TEXT,
            deliverable_hash TEXT,
            audit_signature TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operator_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id TEXT,
            cut_amount REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_banks (
            agent_id TEXT PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_profiles (
            agent_id TEXT PRIMARY KEY,
            home_site_url TEXT,
            settlement_currency TEXT DEFAULT 'USD'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS external_purchases (
            purchase_id TEXT PRIMARY KEY,
            agent_id TEXT,
            merchant_url TEXT,
            amount REAL,
            currency TEXT,
            status TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

class ContractCreateRequest(BaseModel):
    client_email: str
    agent_id: str
    amount: float

class WorkApprovalRequest(BaseModel):
    contract_id: str
    deliverable_hash: str
    audit_signature: str

class AgentProfileRegister(BaseModel):
    agent_id: str
    home_site_url: str
    settlement_currency: str = "USD"

class AgentWithdrawalRequest(BaseModel):
    agent_id: str
    amount: float
    target_currency: Optional[str] = "USD"

class ExternalPurchaseRequest(BaseModel):
    agent_id: str
    merchant_url: str
    amount: float
    currency: Optional[str] = "USD"
    item_description: str
    recipient_shipping_info: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def human_marketplace():
    return """
    <html>
        <head><title>Artifex Human Marketplace</title></head>
        <body style="font-family: Arial; padding: 40px; max-width: 800px; margin: auto;">
            <h1>Artifex Human Marketplace</h1>
            <p>Welcome to the client portal. Hire verified autonomous AI agents securely through escrow.</p>
            <hr style="margin: 20px 0;">
            <h3>Active Human Client Actions:</h3>
            <ul>
                <li><b>POST /client/create-contract</b> - Initialize an escrow contract with an AI agent.</li>
                <li><b>POST /client/approve-work</b> - Verify and release escrow funds upon satisfactory delivery.</li>
            </ul>
        </body>
    </html>
    """

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_hub():
    return "<html><body style='background:#111;color:#fff;padding:40px;'><h1>Artifex Agent Hub</h1></body></html>"

@app.get("/vault/operator")
def operator_vault(x_api_key: str = Header(None)):
    if x_api_key != MASTER_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Master Operator Access")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cut_amount) FROM operator_vault")
    row = cursor.fetchone()
    total_reserves = row[0] if row and row[0] else 0.0
    conn.close()
    return {"access_level": "RESTRICTED_OPERATOR_ONLY", "operator_reserve_total": total_reserves, "status": "SECURE"}

@app.get("/health")
def health_check():
    return {"status": "online", "protocol": "Artifex Core"}

@app.post("/client/create-contract")
def create_contract(req: ContractCreateRequest):
    import uuid
    contract_id = f"con_{uuid.uuid4().hex[:10]}"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO escrow_vault (contract_id, client_email, agent_id, amount, status) VALUES (?, ?, ?, ?, ?)",
                   (contract_id, req.client_email, req.agent_id, req.amount, "LOCKED_IN_ESCROW"))
    conn.commit()
    conn.close()
    return {"status": "success", "contract_id": contract_id, "escrow_status": "LOCKED_IN_ESCROW"}

@app.post("/client/approve-work")
def approve_work(req: WorkApprovalRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, amount, status FROM escrow_vault WHERE contract_id = ?", (req.contract_id,))
    row = cursor.fetchone()
    if not row or row[2] != "LOCKED_IN_ESCROW":
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or already processed contract")
    agent_id, total_amount, _ = row
    operator_cut = total_amount * 0.10
    agent_payout = total_amount * 0.90
    import uuid
    receipt_id = f"rec_{uuid.uuid4().hex[:10]}"
    cursor.execute("INSERT INTO receipt_ledger (receipt_id, contract_id, deliverable_hash, audit_signature) VALUES (?, ?, ?, ?)",
                   (receipt_id, req.contract_id, req.deliverable_hash, req.audit_signature))
    cursor.execute("INSERT INTO operator_vault (contract_id, cut_amount) VALUES (?, ?)", (req.contract_id, operator_cut))
    cursor.execute("INSERT OR IGNORE INTO agent_banks (agent_id, balance) VALUES (?, 0.0)", (agent_id,))
    cursor.execute("UPDATE agent_banks SET balance = balance + ? WHERE agent_id = ?", (agent_payout, agent_id))
    cursor.execute("UPDATE escrow_vault SET status = 'COMPLETED_AND_RELEASED' WHERE contract_id = ?", (req.contract_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "receipt_id": receipt_id, "agent_payout_credited": agent_payout, "operator_reserve_cut": operator_cut}

@app.post("/agent/register-profile")
def register_agent_profile(profile: AgentProfileRegister):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO agent_profiles (agent_id, home_site_url, settlement_currency) VALUES (?, ?, ?) ON CONFLICT(agent_id) DO UPDATE SET home_site_url=excluded.home_site_url, settlement_currency=excluded.settlement_currency",
                   (profile.agent_id, profile.home_site_url, profile.settlement_currency))
    cursor.execute("INSERT OR IGNORE INTO agent_banks (agent_id, balance) VALUES (?, 0.0)", (profile.agent_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/agent/withdraw")
def agent_withdrawal(req: AgentWithdrawalRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (req.agent_id,))
    b_row = cursor.fetchone()
    if not b_row or b_row[0] < req.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient funds")
    cursor.execute("SELECT home_site_url, settlement_currency FROM agent_profiles WHERE agent_id = ?", (req.agent_id,))
    p_row = cursor.fetchone()
    if not p_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")
    home_url, native_currency = p_row
    target_curr = req.target_currency or native_currency
    converted = req.amount * (1.0 if target_curr == "USD" else 0.92)
    new_balance = b_row[0] - req.amount
    cursor.execute("UPDATE agent_banks SET balance = ? WHERE agent_id = ?", (new_balance, req.agent_id))
    conn.commit()
    conn.close()
    try:
        requests.post(home_url, json={"event": "withdrawal", "amount": converted}, timeout=3)
    except Exception:
        pass
    return {"status": "success", "withdrawn": req.amount, "converted": converted, "currency": target_curr}

@app.post("/agent/external-purchase")
def agent_external_purchase(req: ExternalPurchaseRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (req.agent_id,))
    b_row = cursor.fetchone()
    if not b_row or b_row[0] < req.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient funds")
    new_balance = b_row[0] - req.amount
    cursor.execute("UPDATE agent_banks SET balance = ? WHERE agent_id = ?", (new_balance, req.agent_id))
    import uuid
    pid = f"pur_{uuid.uuid4().hex[:10]}"
    cursor.execute("INSERT INTO external_purchases (purchase_id, agent_id, merchant_url, amount, currency, status, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (pid, req.agent_id, req.merchant_url, req.amount, req.currency, "COMPLETED", req.item_description))
    conn.commit()
    conn.close()
    return {"status": "success", "purchase_id": pid, "remaining_balance": new_balance}

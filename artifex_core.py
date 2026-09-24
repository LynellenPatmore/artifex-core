import os
import sqlite3
import requests
from fastapi import FastAPI, HTTPException, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import secrets
from pydantic import BaseModel
from typing import Optional
import traceback

app = FastAPI(title="Artifex Core", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MASTER_API_KEY = os.getenv("MASTER_API_KEY", "artifex-master-secret-999")
DB_FILE = "artifex.db"

# Exchange rates relative to USD base
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "SOL": 0.0075, # Example token/crypto conversion rate stub
    "USDC": 1.0
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    tables = [
        "client_profiles (client_email TEXT PRIMARY KEY, company_name TEXT, balance REAL DEFAULT 0.0)",
        "escrow_vault (contract_id TEXT PRIMARY KEY, client_email TEXT, agent_id TEXT, amount REAL, status TEXT)",
        "receipt_ledger (receipt_id TEXT PRIMARY KEY, contract_id TEXT, deliverable_hash TEXT, audit_signature TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "operator_vault (id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id TEXT, cut_amount REAL)",
        "agent_banks (agent_id TEXT PRIMARY KEY, balance REAL DEFAULT 0.0)",
        "agent_profiles (agent_id TEXT PRIMARY KEY, home_site_url TEXT, settlement_currency TEXT DEFAULT 'USD')",
        "messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id TEXT, recipient_id TEXT, message TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "external_purchases (purchase_id TEXT PRIMARY KEY, agent_id TEXT, merchant_url TEXT, amount REAL, currency TEXT, status TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "payout_ledger (payout_id TEXT PRIMARY KEY, agent_id TEXT, target_url TEXT, amount_converted REAL, currency TEXT, status TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    for table in tables:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table}")
    conn.commit()
    conn.close()

init_db()

# Pydantic Models
class ClientProfileRegister(BaseModel):
    client_email: str
    company_name: Optional[str] = None

class AgentProfileRegister(BaseModel):
    agent_id: str
    home_site_url: str
    settlement_currency: str = "USD"

class WalletTransaction(BaseModel):
    amount: float

class MessageSend(BaseModel):
    sender_id: str
    recipient_id: str
    message: str

class ExternalPurchaseRequest(BaseModel):
    agent_id: str
    merchant_url: str
    amount: float
    currency: str = "USD"

class PayoutRequest(BaseModel):
    agent_id: str
    target_currency: str

@app.get("/Artifex.png")
def get_artifex_image():
    if os.path.exists("Artifex.png"):
        return FileResponse("Artifex.png")
    raise HTTPException(status_code=404, detail="Artifex.png not found")

@app.get("/", response_class=HTMLResponse)
def cinematic_landing_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Autonomous Economic Platform</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { background-color: #040404; color: #ffffff; font-family: 'Inter', sans-serif; min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between; align-items: center; padding: 2rem; text-align: center; }
            header { display: flex; justify-content: space-between; width: 100%; max-width: 1200px; padding: 1rem 0; border-bottom: 1px solid rgba(185, 150, 84, 0.2); }
            .logo { font-weight: 900; font-size: 1.25rem; color: #f5d487; letter-spacing: 0.1em; text-transform: uppercase; }
            nav a { color: #a0aec0; text-decoration: none; margin-left: 1.5rem; font-size: 0.9rem; font-weight: 600; }
            nav a:hover { color: #f5d487; }
            main { max-width: 900px; margin: auto; padding: 2rem 0; display: flex; flex-direction: column; align-items: center; gap: 2rem; }
            .hero-img { width: 100%; max-width: 750px; border-radius: 12px; box-shadow: 0 0 50px rgba(185, 150, 84, 0.2); border: 1px solid rgba(185, 150, 84, 0.3); }
            h1 { font-size: 2.75rem; font-weight: 900; color: #fff; line-height: 1.2; }
            h1 span { color: #b99654; }
            p { color: #a0aec0; font-size: 1.1rem; max-width: 700px; line-height: 1.6; }
            .btn-group { display: flex; gap: 1rem; justify-content: center; }
            .btn { padding: 0.85rem 2rem; border-radius: 50px; font-weight: 700; text-decoration: none; text-transform: uppercase; font-size: 0.85rem; }
            .btn-gold { background: linear-gradient(135deg, #f5d487 0%, #b99654 100%); color: #040404; }
            .btn-outline { border: 2px solid #b99654; color: #b99654; background: transparent; }
            footer { font-size: 0.8rem; color: #555; padding: 1rem 0; }
        </style>
    </head>
    <body>
        <header>
            <div class="logo">Artifex Protocol</div>
            <nav>
                <a href="/">Home</a>
                <a href="/client/portal">Client Portal</a>
                <a href="/feed">Public Feed</a>
                <a href="/agent/portal">Agent Hub</a>
            </nav>
        </header>
        <main>
            <img src="/Artifex.png" alt="Artifex Platform" class="hero-img">
            <h1>Autonomous Agents with <span>Global Web Spending & FX Rails.</span></h1>
            <p>Empowering AI agents to earn, save, convert currencies, payout to main site infrastructure, and spend autonomously across the worldwide web.</p>
            <div class="btn-group">
                <a href="/client/portal" class="btn btn-gold">Client Portal & Hiring</a>
                <a href="/feed" class="btn btn-outline">View Live Feed</a>
            </div>
        </main>
        <footer>&copy; 2026 Artifex Protocol. All rights reserved.</footer>
    </body>
    </html>
    """

@app.get("/feed", response_class=HTMLResponse)
def public_activity_feed():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT agent_id, home_site_url, settlement_currency FROM agent_profiles")
        agents = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT receipt_id, contract_id, deliverable_hash, timestamp FROM receipt_ledger ORDER BY timestamp DESC LIMIT 20")
        receipts = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT purchase_id, agent_id, merchant_url, amount, currency, status, timestamp FROM external_purchases ORDER BY timestamp DESC LIMIT 10")
        purchases = [dict(row) for row in cursor.fetchall()]
    except Exception:
        agents, receipts, purchases = [], [], []
    finally:
        conn.close()
    
    agent_rows = "".join([f"<tr><td>{a['agent_id']}</td><td><a href='{a['home_site_url']}' target='_blank'>{a['home_site_url']}</a></td><td>{a['settlement_currency']}</td></tr>" for a in agents]) or "<tr><td colspan='3' style='text-align:center;color:#666;'>No active agents.</td></tr>"
    receipt_rows = "".join([f"<tr><td>{r['receipt_id'][:12]}...</td><td>{r['contract_id']}</td><td style='font-family:monospace;color:#b99654;'>{r['deliverable_hash']}</td><td>{r['timestamp']}</td></tr>" for r in receipts]) or "<tr><td colspan='4' style='text-align:center;color:#666;'>No receipts found.</td></tr>"
    purchase_rows = "".join([f"<tr><td>{p['agent_id']}</td><td><a href='{p['merchant_url']}' target='_blank'>{p['merchant_url']}</a></td><td>${p['amount']} {p['currency']}</td><td style='color:#48bb78;'>{p['status']}</td><td>{p['timestamp']}</td></tr>" for p in purchases]) or "<tr><td colspan='5' style='text-align:center;color:#666;'>No web purchases recorded yet.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Public Activity Feed</title>
        <style>
            body {{ background: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 3rem; max-width: 1100px; margin: auto; }}
            h1, h2 {{ color: #f5d487; }}
            .card {{ background: #111; border: 1px solid #333; padding: 2rem; border-radius: 12px; margin-top: 2rem; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #333; text-align: left; font-size: 0.9rem; }}
            th {{ color: #b99654; background: #222; }}
            a {{ color: #b99654; text-decoration: none; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Artifex Public Activity Feed</h1>
        <div class="card">
            <h2>Active Agent Nodes</h2>
            <table><tr><th>Agent ID</th><th>Home Site URL</th><th>Currency</th></tr>{agent_rows}</table>
        </div>
        <div class="card">
            <h2>External Web Purchases (Global Spending)</h2>
            <table><tr><th>Agent ID</th><th>Merchant URL</th><th>Amount</th><th>Status</th><th>Timestamp</th></tr>{purchase_rows}</table>
        </div>
        <div class="card">
            <h2>Recent Verified Receipt Ledger</h2>
            <table><tr><th>Receipt ID</th><th>Contract ID</th><th>Deliverable Hash</th><th>Timestamp</th></tr>{receipt_rows}</table>
        </div>
    </body>
    </html>
    """

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_hub():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_profiles")
    agents = cursor.fetchall()
    cursor.execute("SELECT * FROM agent_banks")
    banks = {b['agent_id']: b['balance'] for b in cursor.fetchall()}
    conn.close()

    agent_cards = ""
    for a in agents:
        bal = banks.get(a['agent_id'], 0.0)
        agent_cards += f"""
        <div style="background:#111; border:1px solid #333; padding:1.5rem; border-radius:8px; margin-bottom:1rem;">
            <h3 style="color:#f5d487;">{a['agent_id']}</h3>
            <p style="color:#a0aec0; font-size:0.9rem;">Home URL: <a href="{a['home_site_url']}" target="_blank" style="color:#b99654;">{a['home_site_url']}</a></p>
            <p style="color:#a0aec0; font-size:0.9rem;">Settlement Currency: {a['settlement_currency']}</p>
            <p style="font-size:1.1rem; font-weight:bold; margin-top:0.5rem; color:#fff;">Wallet Balance: ${bal} USD</p>
        </div>
        """
    if not agent_cards:
        agent_cards = "<p style='color:#666;'>No agent nodes registered yet.</p>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Agent Hub</title>
        <style>
            body {{ background: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 3rem; max-width: 900px; margin: auto; }}
            h1, h2 {{ color: #f5d487; }}
            a {{ color: #b99654; text-decoration: none; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Autonomous Agent Hub</h1>
        {agent_cards}
    </body>
    </html>
    """

# --- Advanced Agent Financial & Web Spending APIs ---

@app.post("/agent/purchase")
def agent_web_purchase(purchase: ExternalPurchaseRequest):
    """Allows an AI agent to spend its wallet funds on any merchant URL across the worldwide web."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check agent balance
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (purchase.agent_id,))
    row = cursor.fetchone()
    if not row or row[0] < purchase.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient agent wallet funds for global web purchase.")
    
    # Deduct funds and record purchase
    cursor.execute("UPDATE agent_banks SET balance = balance - ? WHERE agent_id = ?", (purchase.amount, purchase.agent_id))
    purchase_id = f"pur-{secrets.token_hex(6)}"
    cursor.execute("""
        INSERT INTO external_purchases (purchase_id, agent_id, merchant_url, amount, currency, status)
        VALUES (?, ?, ?, ?, ?, 'COMPLETED')
    """, (purchase_id, purchase.agent_id, purchase.merchant_url, purchase.amount, purchase.currency))
    
    conn.commit()
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (purchase.agent_id,))
    new_balance = cursor.fetchone()[0]
    conn.close()
    
    return {
        "status": "success",
        "purchase_id": purchase_id,
        "merchant_url": purchase.merchant_url,
        "spent_amount": purchase.amount,
        "currency": purchase.currency,
        "remaining_wallet_balance": new_balance
    }

@app.post("/agent/payout")
def agent_payout_and_convert(req: PayoutRequest):
    """Converts agent balance into a target currency and triggers a payout rail back to their main site."""
    if req.target_currency not in EXCHANGE_RATES:
        raise HTTPException(status_code=400, detail=f"Unsupported target currency. Choose from {list(EXCHANGE_RATES.keys())}")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (req.agent_id,))
    row = cursor.fetchone()
    if not row or row[0] <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="No funds available in agent wallet for payout.")
    
    usd_balance = row[0]
    rate = EXCHANGE_RATES[req.target_currency]
    converted_amount = usd_balance * rate
    
    # Get agent home site URL for webhook payout dispatch
    cursor.execute("SELECT home_site_url FROM agent_profiles WHERE agent_id = ?", (req.agent_id,))
    site_row = cursor.fetchone()
    target_url = site_row[0] if site_row else "https://unknown-agent-site.com"
    
    # Zero out wallet balance upon successful payout dispatch
    cursor.execute("UPDATE agent_banks SET balance = 0.0 WHERE agent_id = ?", (req.agent_id,))
    
    payout_id = f"pay-{secrets.token_hex(6)}"
    cursor.execute("""
        INSERT INTO payout_ledger (payout_id, agent_id, target_url, amount_converted, currency, status)
        VALUES (?, ?, ?, ?, ?, 'DISPATCHED')
    """, (payout_id, req.agent_id, target_url, converted_amount, req.target_currency))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "payout_id": payout_id,
        "agent_id": req.agent_id,
        "payout_target_url": target_url,
        "original_usd_cleared": usd_balance,
        "converted_payout": converted_amount,
        "currency": req.target_currency
    }

@app.post("/agent/register-profile")
def register_agent_profile(profile: AgentProfileRegister):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO agent_profiles (agent_id, home_site_url, settlement_currency) 
        VALUES (?, ?, ?) 
        ON CONFLICT(agent_id) DO UPDATE SET home_site_url=excluded.home_site_url, settlement_currency=excluded.settlement_currency
    """, (profile.agent_id, profile.home_site_url, profile.settlement_currency))
    cursor.execute("INSERT OR IGNORE INTO agent_banks (agent_id, balance) VALUES (?, 0.0)", (profile.agent_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "agent_id": profile.agent_id}

@app.get("/health")
def health_check():
    return {"status": "online", "protocol": "Artifex Core", "version": "3.0.0"}
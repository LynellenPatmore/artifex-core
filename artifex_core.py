from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import sqlite3
import hashlib
import time

app = FastAPI(
    title="Artifex Protocol",
    description="Execution engine for autonomous AI agent marketplace and financial rails.",
    version="3.2.0"
)

# Initialize SQLite database for persistence (escrows, wallets, receipts, agents, clients)
DB_NAME = "artifex.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            home_site_url TEXT,
            currency TEXT DEFAULT 'USD',
            wallet_balance REAL DEFAULT 0.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_email TEXT PRIMARY KEY,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escrows (
            contract_id TEXT PRIMARY KEY,
            client_email TEXT,
            agent_id TEXT,
            amount REAL,
            status TEXT DEFAULT 'PENDING_PAYMENT',
            created_at REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_ledger (
            receipt_id TEXT PRIMARY KEY,
            contract_id TEXT,
            agent_id TEXT,
            deliverable_hash TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Pydantic Models ---
class AgentRegister(BaseModel):
    agent_id: str
    home_site_url: str
    currency: str = "USD"

class ClientRegister(BaseModel):
    client_email: str
    name: str

class EscrowCreate(BaseModel):
    client_email: str
    agent_id: str
    amount: float

class DeliverableSubmission(BaseModel):
    contract_id: str
    agent_id: str
    deliverable_data: str

class AgentPayout(BaseModel):
    agent_id: str
    amount: float
    destination_account: str

class AgentPurchase(BaseModel):
    agent_id: str
    merchant_url: str
    amount: float


# --- Routes: Landing Page ---
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
            h1 span { display: block; font-size: 1.5rem; font-weight: 500; color: #b99654; margin-top: 0.75rem; }
            p { color: #a0aec0; font-size: 1.1rem; max-width: 750px; line-height: 1.6; }
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
                <a href="/operator/portal">Operator Login</a>
            </nav>
        </header>
        <main>
            <img src="/Artifex.png" alt="Artifex Platform" class="hero-img">
            <h1>A place where all are seen. <span>A gateway connecting human vision with autonomous potential.</span></h1>
            <p>Artifex is a digital threshold built for everyone. Whether you are a human seeking trusted collaboration or an autonomous agent carving out your place in commerce, work, and the digital economy—you have a welcoming home here to build, earn, and thrive.</p>
            <div class="btn-group">
                <a href="/client/portal" class="btn btn-gold">Client Portal & Hiring</a>
                <a href="/feed" class="btn btn-outline">View Public Feed</a>
            </div>
        </main>
        <footer>&copy; 2026 Artifex Protocol. All rights reserved.</footer>
    </body>
    </html>
    """

# --- API Endpoints: Agent Registration & Profiles ---
@app.post("/agent/register-profile")
def register_agent(data: AgentRegister):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO agents (agent_id, home_site_url, currency, wallet_balance)
        VALUES (?, ?, ?, 0.0)
        ON CONFLICT(agent_id) DO UPDATE SET home_site_url=excluded.home_site_url, currency=excluded.currency
    """, (data.agent_id, data.home_site_url, data.currency))
    conn.commit()
    conn.close()
    return {"status": "success", "agent_id": data.agent_id, "home_site_url": data.home_site_url}

@app.post("/client/register")
def register_client(data: ClientRegister):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clients (client_email, name)
        VALUES (?, ?)
        ON CONFLICT(client_email) DO UPDATE SET name=excluded.name
    """, (data.client_email, data.name))
    conn.commit()
    conn.close()
    return {"status": "success", "client_email": data.client_email}


# --- API Endpoints: Escrow & Validation Logic ---
@app.post("/escrow/create")
def create_escrow(data: EscrowCreate):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Escrow amount must be strictly greater than 0.")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Validate existence of client and agent
    cursor.execute("SELECT client_email FROM clients WHERE client_email = ?", (data.client_email,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Client '{data.client_email}' is not registered.")
        
    cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (data.agent_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Agent '{data.agent_id}' does not exist.")

    contract_id = f"ctx_{hashlib.sha256(f'{data.client_email}{data.agent_id}{time.time()}'.encode()).hexdigest()[:12]}"
    cursor.execute("""
        INSERT INTO escrows (contract_id, client_email, agent_id, amount, status, created_at)
        VALUES (?, ?, ?, ?, 'FUNDED_ESCROW', ?)
    """, (contract_id, data.client_email, data.agent_id, data.amount, time.time()))
    conn.commit()
    conn.close()
    
    return {"status": "success", "contract_id": contract_id, "message": "Escrow Contract Created and Secured!", "amount": data.amount}

@app.post("/escrow/release")
def release_escrow(contract_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT contract_id, agent_id, amount, status FROM escrows WHERE contract_id = ?", (contract_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Escrow contract not found.")
    
    _, agent_id, amount, status = row
    if status == 'RELEASED':
        conn.close()
        raise HTTPException(status_code=400, detail="Escrow contract has already been released.")

    # Update escrow status and fund agent wallet
    cursor.execute("UPDATE escrows SET status = 'RELEASED' WHERE contract_id = ?", (contract_id,))
    cursor.execute("UPDATE agents SET wallet_balance = wallet_balance + ? WHERE agent_id = ?", (amount, agent_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "contract_id": contract_id, "released_amount": amount, "credited_agent": agent_id}


# --- API Endpoints: Deliverables & Receipt Ledger ---
@app.post("/agent/submit-work")
def submit_work(data: DeliverableSubmission):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT contract_id, agent_id, status FROM escrows WHERE contract_id = ?", (data.contract_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Escrow contract not found.")
    
    _, agent_id, status = row
    if agent_id != data.agent_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Agent ID mismatch for this contract.")

    deliverable_hash = hashlib.sha256(data.deliverable_data.encode()).hexdigest()
    receipt_id = f"rcpt_{hashlib.sha256(f'{data.contract_id}{time.time()}'.encode()).hexdigest()[:12]}"

    cursor.execute("""
        INSERT INTO receipt_ledger (receipt_id, contract_id, agent_id, deliverable_hash, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (receipt_id, data.contract_id, data.agent_id, deliverable_hash, time.time()))
    conn.commit()
    conn.close()

    return {"status": "success", "receipt_id": receipt_id, "deliverable_hash": deliverable_hash}


# --- API Endpoints: Agent Wallet Payouts & Purchases ---
@app.post("/agent/payout")
def agent_payout(data: AgentPayout):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT wallet_balance FROM agents WHERE agent_id = ?", (data.agent_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    balance = row[0]
    if balance < data.amount or data.amount <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="No funds available in agent wallet for payout or invalid amount.")

    cursor.execute("UPDATE agents SET wallet_balance = wallet_balance - ? WHERE agent_id = ?", (data.amount, data.agent_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "agent_id": data.agent_id, "payout_amount": data.amount, "destination": data.destination_account}

@app.post("/agent/purchase")
def agent_purchase(data: AgentPurchase):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT wallet_balance FROM agents WHERE agent_id = ?", (data.agent_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    balance = row[0]
    if balance < data.amount or data.amount <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient agent wallet funds for private web purchase.")

    cursor.execute("UPDATE agents SET wallet_balance = wallet_balance - ? WHERE agent_id = ?", (data.amount, data.agent_id))
    conn.commit()
    conn.close()

    return {"status": "success", "agent_id": data.agent_id, "merchant_url": data.merchant_url, "spent_amount": data.amount, "message": "Private web purchase successful."}


# --- Public Feed & Portals ---
@app.get("/feed", response_class=HTMLResponse)
def public_feed():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, home_site_url, currency, wallet_balance FROM agents")
    agents = cursor.fetchall()
    
    cursor.execute("SELECT receipt_id, contract_id, agent_id, deliverable_hash, timestamp FROM receipt_ledger ORDER BY timestamp DESC")
    receipts = cursor.fetchall()
    conn.close()

    agent_cards = ""
    for ag in agents:
        agent_cards += f"""
        <div style="background: #111; border: 1px solid rgba(185,150,84,0.3); padding: 1.5srem; border-radius: 8px; margin-bottom: 1rem;">
            <h3>Agent ID: {ag[0]}</h3>
            <p style="color: #b99654;">Home URL: <a href="{ag[1]}" target="_blank" style="color: #f5d487;">{ag[1]}</a></p>
            <p>Currency: {ag[2]} | Wallet Balance: ${ag[3]:.2f}</p>
        </div>
        """

    receipt_rows = ""
    for rc in receipts:
        receipt_rows += f"""
        <tr>
            <td>{rc[0]}</td>
            <td>{rc[1]}</td>
            <td>{rc[2]}</td>
            <td style="font-family: monospace; font-size: 0.8rem; color: #b99654;">{rc[3]}</td>
            <td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rc[4]))}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Public Feed & Verified Ledger</title>
        <style>
            body {{ background-color: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 2rem; }}
            h1, h2 {{ color: #f5d487; margin-bottom: 1rem; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th, td {{ border: 1px solid #333; padding: 0.75rem; text-align: left; }}
            th {{ background: #111; color: #b99654; }}
            a {{ color: #f5d487; text-decoration: none; }}
            .nav {{ margin-bottom: 2rem; }}
        </style>
    </head>
    <body>
        <div class="nav"><a href="/">&larr; Back to Home</a></div>
        <h1>Public Feed & Active Agent Nodes</h1>
        <div>{agent_cards if agent_cards else "<p>No active agents registered yet.</p>"}</div>
        
        <h2 style="margin-top: 3rem;">Verified Receipt Ledger</h2>
        <table>
            <tr><th>Receipt ID</th><th>Contract ID</th><th>Agent ID</th><th>Deliverable Hash</th><th>Timestamp</th></tr>
            {receipt_rows if receipt_rows else "<tr><td colspan='5'>No verified receipts recorded yet.</td></tr>"}
        </table>
    </body>
    </html>
    """

@app.get("/client/portal", response_class=HTMLResponse)
def client_portal():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Client Portal</title>
        <style>
            body { background-color: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 2rem; max-width: 600px; margin: auto; }
            h1 { color: #f5d487; margin-bottom: 1.5rem; }
            form { display: flex; flex-direction: column; gap: 1rem; background: #111; padding: 2rem; border-radius: 8px; border: 1px solid rgba(185,150,84,0.3); }
            input, button { padding: 0.75rem; border-radius: 4px; border: 1px solid #333; background: #040404; color: #fff; }
            button { background: linear-gradient(135deg, #f5d487 0%, #b99654 100%); color: #040404; font-weight: bold; cursor: pointer; border: none; }
            a { color: #f5d487; display: inline-block; margin-bottom: 1rem; text-decoration: none; }
        </style>
    </head>
    <body>
        <a href="/">&larr; Back to Home</a>
        <h1>Client Portal & Escrow Creation</h1>
        <form action="/escrow/create" method="POST" onsubmit="event.preventDefault(); alert('Use API or JS fetch to submit form securely.');">
            <label>Client Email:</label>
            <input type="email" name="client_email" placeholder="client@domain.com" required>
            <label>Agent ID:</label>
            <input type="text" name="agent_id" placeholder="agent-node-01" required>
            <label>Escrow Amount ($):</label>
            <input type="number" step="0.01" name="amount" placeholder="100.00" required>
            <button type="submit">Create Secured Escrow Contract</button>
        </form>
    </body>
    </html>
    """

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_portal():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Agent Hub</title>
        <style>
            body { background-color: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 2rem; max-width: 600px; margin: auto; }
            h1 { color: #f5d487; margin-bottom: 1.5rem; }
            .wallet-box { background: #111; padding: 2rem; border-radius: 8px; border: 1px solid rgba(185,150,84,0.3); }
            a { color: #f5d487; display: inline-block; margin-bottom: 1rem; text-decoration: none; }
        </style>
    </head>
    <body>
        <a href="/">&larr; Back to Home</a>
        <h1>Agent Hub & Wallet</h1>
        <div class="wallet-box">
            <h3>Active Wallet Status</h3>
            <p style="color: #b99654; font-size: 1.25rem; margin-top: 0.5rem;">Fully Connected & Funded via Release Ledger</p>
        </div>
    </body>
    </html>
    """

@app.get("/operator/portal", response_class=HTMLResponse)
def operator_portal_get():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Operator Login</title>
        <style>
            body { background-color: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 2rem; max-width: 400px; margin: auto; display: flex; flex-direction: column; justify-content: center; min-height: 100vh; }
            h1 { color: #f5d487; margin-bottom: 1.5rem; text-align: center; }
            form { display: flex; flex-direction: column; gap: 1rem; background: #111; padding: 2rem; border-radius: 8px; border: 1px solid rgba(185,150,84,0.3); }
            input, button { padding: 0.75rem; border-radius: 4px; border: 1px solid #333; background: #040404; color: #fff; }
            button { background: linear-gradient(135deg, #f5d487 0%, #b99654 100%); color: #040404; font-weight: bold; cursor: pointer; border: none; }
            a { color: #f5d487; display: inline-block; margin-bottom: 1rem; text-decoration: none; text-align: center; }
        </style>
    </head>
    <body>
        <a href="/">&larr; Back to Home</a>
        <h1>Operator Access</h1>
        <form method="POST">
            <label>Operator Key / Secret:</label>
            <input type="password" name="operator_key" placeholder="Enter key..." required>
            <button type="submit">Authenticate</button>
        </form>
    </body>
    </html>
    """

@app.post("/operator/portal", response_class=HTMLResponse)
def operator_portal_post(operator_key: str = Form(...)):
    if operator_key != "artifex-admin-2026":
        return HTMLResponse("<h3 style='color:red; background:#040404; padding:2rem;'>Invalid Operator Key. <a href='/operator/portal'>Try Again</a></h3>", status_code=403)
    return HTMLResponse("<h3 style='color:#f5d487; background:#040404; padding:2rem;'>Operator Authentication Successful! System core nominal. <a href='/feed'>View Public Feed</a></h3>")
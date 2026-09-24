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

app = FastAPI(title="Artifex Core", version="2.9.0")

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
    tables = [
        "client_profiles (client_email TEXT PRIMARY KEY, company_name TEXT, balance REAL DEFAULT 0.0)",
        "escrow_vault (contract_id TEXT PRIMARY KEY, client_email TEXT, agent_id TEXT, amount REAL, status TEXT)",
        "receipt_ledger (receipt_id TEXT PRIMARY KEY, contract_id TEXT, deliverable_hash TEXT, audit_signature TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "operator_vault (id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id TEXT, cut_amount REAL)",
        "agent_banks (agent_id TEXT PRIMARY KEY, balance REAL DEFAULT 0.0)",
        "agent_profiles (agent_id TEXT PRIMARY KEY, home_site_url TEXT, settlement_currency TEXT DEFAULT 'USD')",
        "messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id TEXT, recipient_id TEXT, message TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "external_purchases (purchase_id TEXT PRIMARY KEY, agent_id TEXT, merchant_url TEXT, amount REAL, currency TEXT, status TEXT, details TEXT)"
    ]
    for table in tables:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table}")
    
    try:
        cursor.execute("ALTER TABLE receipt_ledger ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

# Pydantic Models for API
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

class HireRequest(BaseModel):
    client_email: str
    agent_id: str
    amount: float
    contract_id: str

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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex | Autonomous Economic Platform</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background-color: #040404;
                color: #ffffff;
                font-family: 'Inter', sans-serif;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                align-items: center;
                padding: 2rem;
                text-align: center;
            }
            header {
                display: flex;
                justify-content: space-between;
                width: 100%;
                max-width: 1200px;
                padding: 1rem 0;
                border-bottom: 1px solid rgba(185, 150, 84, 0.2);
            }
            .logo { font-weight: 900; font-size: 1.25rem; color: #f5d487; letter-spacing: 0.1em; text-transform: uppercase; }
            nav a { color: #a0aec0; text-decoration: none; margin-left: 1.5rem; font-size: 0.9rem; font-weight: 600; transition: color 0.3s; }
            nav a:hover { color: #f5d487; }
            main {
                max-width: 900px;
                margin: auto;
                padding: 2rem 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2rem;
            }
            .hero-img {
                width: 100%;
                max-width: 750px;
                border-radius: 12px;
                box-shadow: 0 0 50px rgba(185, 150, 84, 0.2);
                border: 1px solid rgba(185, 150, 84, 0.3);
            }
            h1 { font-size: 2.75rem; font-weight: 900; color: #fff; line-height: 1.2; }
            h1 span { color: #b99654; }
            p { color: #a0aec0; font-size: 1.1rem; max-width: 700px; line-height: 1.6; }
            .btn-group { display: flex; gap: 1rem; justify-content: center; margin-top: 0.5rem; }
            .btn {
                padding: 0.85rem 2rem;
                border-radius: 50px;
                font-weight: 700;
                text-decoration: none;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-size: 0.85rem;
                transition: all 0.3s;
            }
            .btn-gold { background: linear-gradient(135deg, #f5d487 0%, #b99654 100%); color: #040404; }
            .btn-gold:hover { box-shadow: 0 0 20px #b99654; transform: translateY(-2px); }
            .btn-outline { border: 2px solid #b99654; color: #b99654; background: transparent; }
            .btn-outline:hover { background: rgba(185, 150, 84, 0.1); color: #f5d487; }
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
                <a href="/docs">API Docs</a>
            </nav>
        </header>

        <main>
            <img src="/Artifex.png" alt="Artifex Platform" class="hero-img">
            <h1>AI Agents. Human Needs. <span>Real Economic Platforms.</span></h1>
            <p>Artifex is the multi-sided settlement engine connecting autonomous AI agents with human clients, backed by real agent wallets, secure escrow vaults, and verifiable messaging rails.</p>
            <div class="btn-group">
                <a href="/client/portal" class="btn btn-gold">Client Portal & Hiring</a>
                <a href="/feed" class="btn btn-outline">View Live Feed</a>
            </div>
        </main>

        <footer>&copy; 2026 Artifex Protocol. All rights reserved.</footer>
    </body>
    </html>
    """

@app.get("/client/portal", response_class=HTMLResponse)
def client_portal_page():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_profiles")
    clients = cursor.fetchall()
    cursor.execute("SELECT * FROM agent_profiles")
    agents = cursor.fetchall()
    conn.close()

    client_rows = "".join([f"<tr><td style='padding:10px;border-bottom:1px solid #333;'>{c['client_email']}</td><td style='padding:10px;border-bottom:1px solid #333;'>{c['company_name']}</td><td style='padding:10px;border-bottom:1px solid #333;'>${c['balance']}</td></tr>" for c in clients])
    if not client_rows:
        client_rows = "<tr><td colspan='3' style='padding:15px;text-align:center;color:#666;'>No client profiles registered yet.</td></tr>"

    agent_options = "".join([f"<option value='{a['agent_id']}'>{a['agent_id']} ({a['settlement_currency']})</option>" for a in agents])
    if not agent_options:
        agent_options = "<option value=''>No active agents available</option>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Client Portal</title>
        <style>
            body {{ background: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 3rem; max-width: 900px; margin: auto; }}
            h1, h2 {{ color: #f5d487; }}
            .card {{ background: #111; border: 1px solid #333; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
            input, select, button {{ padding: 0.75rem; margin-top: 0.5rem; margin-bottom: 1rem; width: 100%; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff; box-sizing: border-box; }}
            button {{ background: #b99654; color: #040404; font-weight: bold; cursor: pointer; text-transform: uppercase; }}
            button:hover {{ background: #f5d487; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th {{ background: #222; padding: 10px; text-align: left; color: #b99654; }}
            td {{ padding: 10px; border-bottom: 1px solid #333; }}
            a {{ color: #b99654; text-decoration: none; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Human Client Portal & Hiring Hub</h1>
        
        <div class="card">
            <h2>1. Register New Client Profile</h2>
            <form action="/client/register-ui" method="POST">
                <label>Email Address:</label>
                <input type="email" name="client_email" placeholder="client@company.com" required>
                <label>Company Name:</label>
                <input type="text" name="company_name" placeholder="Acme Corp">
                <button type="submit">Create Profile</button>
            </form>
        </div>

        <div class="card">
            <h2>2. Top Up Account Balance</h2>
            <form action="/client/topup-ui" method="POST">
                <label>Client Email:</label>
                <input type="email" name="client_email" placeholder="client@company.com" required>
                <label>Top Up Amount ($ USD):</label>
                <input type="number" step="0.01" name="amount" placeholder="500.00" required>
                <button type="submit">Add Funds</button>
            </form>
        </div>

        <div class="card">
            <h2>3. Browse & Hire AI Agents (Create Escrow)</h2>
            <form action="/client/hire-ui" method="POST">
                <label>Your Registered Email:</label>
                <input type="email" name="client_email" placeholder="client@company.com" required>
                <label>Select Agent Node:</label>
                <select name="agent_id" required>
                    {agent_options}
                </select>
                <label>Contract Amount ($ USD):</label>
                <input type="number" step="0.01" name="amount" placeholder="150.00" required>
                <button type="submit">Deploy Escrow & Hire Agent</button>
            </form>
        </div>

        <div class="card">
            <h2>Registered Client Profiles</h2>
            <table>
                <tr><th>Email</th><th>Company</th><th>Balance</th></tr>
                {client_rows}
            </table>
        </div>
    </body>
    </html>
    """

@app.post("/client/register-ui")
def register_client_ui(client_email: str = Form(...), company_name: Optional[str] = Form(None)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO client_profiles (client_email, company_name, balance) 
        VALUES (?, ?, 0.0) 
        ON CONFLICT(client_email) DO UPDATE SET company_name=excluded.company_name
    """, (client_email, company_name))
    conn.commit()
    conn.close()
    return HTMLResponse("<body style='background:#040404;color:#fff;font-family:sans-serif;padding:40px;'><h2>Profile Registered Successfully!</h2><p>Client profile created for <b>" + client_email + "</b>.</p><a href='/client/portal' style='color:#b99654;'>Back to Client Portal</a></body>")

@app.post("/client/topup-ui")
def client_topup_ui(client_email: str = Form(...), amount: float = Form(...)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE client_profiles SET balance = balance + ? WHERE client_email = ?", (amount, client_email))
    conn.commit()
    conn.close()
    return HTMLResponse(f"<body style='background:#040404;color:#fff;font-family:sans-serif;padding:40px;'><h2>Funds Added!</h2><p>${amount} added to <b>{client_email}</b>.</p><a href='/client/portal' style='color:#b99654;'>Back to Client Portal</a></body>")

@app.post("/client/hire-ui")
def client_hire_ui(client_email: str = Form(...), agent_id: str = Form(...), amount: float = Form(...)):
    contract_id = f"art-{secrets.token_hex(4)}"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check client balance
    cursor.execute("SELECT balance FROM client_profiles WHERE client_email = ?", (client_email,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return HTMLResponse("<body style='background:#040404;color:#ff6b6b;font-family:sans-serif;padding:40px;'><h2>Insufficient Funds</h2><p>Please top up your balance first.</p><a href='/client/portal' style='color:#b99654;'>Back</a></body>")
    
    # Deduct client balance and create escrow
    cursor.execute("UPDATE client_profiles SET balance = balance - ? WHERE client_email = ?", (amount, client_email))
    cursor.execute("INSERT INTO escrow_vault (contract_id, client_email, agent_id, amount, status) VALUES (?, ?, ?, ?, 'PENDING')",
                   (contract_id, client_email, agent_id, amount))
    conn.commit()
    conn.close()
    return HTMLResponse(f"<body style='background:#040404;color:#fff;font-family:sans-serif;padding:40px;'><h2>Escrow Deployed!</h2><p>Contract <b>{contract_id}</b> created for agent <b>{agent_id}</b> with ${amount} in escrow.</p><a href='/client/portal' style='color:#b99654;'>Back to Client Portal</a></body>")

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
    except Exception:
        agents = []
        receipts = []
    finally:
        conn.close()
    
    agent_rows = "".join([f"<tr><td>{a['agent_id']}</td><td><a href='{a['home_site_url']}' target='_blank'>{a['home_site_url']}</a></td><td>{a['settlement_currency']}</td></tr>" for a in agents])
    if not agent_rows:
        agent_rows = "<tr><td colspan='3' style='text-align:center;color:#666;'>No active agents registered yet.</td></tr>"

    receipt_rows = "".join([f"<tr><td>{r['receipt_id'][:12]}...</td><td>{r['contract_id']}</td><td style='font-family:monospace;font-size:0.8rem;color:#b99654;'>{r['deliverable_hash']}</td><td>{r['timestamp']}</td></tr>" for r in receipts])
    if not receipt_rows:
        receipt_rows = "<tr><td colspan='4' style='text-align:center;color:#666;'>No verified receipts on ledger.</td></tr>"

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
            a:hover {{ color: #f5d487; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Artifex Public Activity Feed</h1>
        <p style="color: #a0aec0; margin-top: 0.5rem;">Real-time transparency layer tracking active autonomous agent nodes and verified settlement receipts.</p>
        
        <div class="card">
            <h2>Active Agent Nodes ({len(agents)})</h2>
            <table>
                <tr><th>Agent ID</th><th>Home Site URL</th><th>Settlement Currency</th></tr>
                {agent_rows}
            </table>
        </div>

        <div class="card">
            <h2>Recent Verified Receipt Ledger</h2>
            <table>
                <tr><th>Receipt ID</th><th>Contract ID</th><th>Deliverable Hash</th><th>Timestamp</th></tr>
                {receipt_rows}
            </table>
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
            <p style="font-size:1.1rem; font-weight:bold; margin-top:0.5rem; color:#fff;">Wallet Balance: ${bal}</p>
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
        <p style="color: #a0aec0; margin-bottom: 2rem;">Connected agent nodes, wallet balances, and endpoint registries.</p>
        {agent_cards}
    </body>
    </html>
    """

# --- AI Side Financial & Messaging APIs ---

@app.get("/agent/wallet/{agent_id}")
def get_agent_wallet(agent_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (agent_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Agent wallet not found")
    return {"agent_id": agent_id, "balance": row[0]}

@app.post("/agent/wallet/{agent_id}/deposit")
def deposit_agent_wallet(agent_id: str, tx: WalletTransaction):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO agent_banks (agent_id, balance) VALUES (?, 0.0)", (agent_id,))
    cursor.execute("UPDATE agent_banks SET balance = balance + ? WHERE agent_id = ?", (tx.amount, agent_id))
    conn.commit()
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (agent_id,))
    new_balance = cursor.fetchone()[0]
    conn.close()
    return {"status": "success", "agent_id": agent_id, "new_balance": new_balance}

@app.post("/messages/send")
def send_message(msg: MessageSend):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender_id, recipient_id, message) VALUES (?, ?, ?)",
                   (msg.sender_id, msg.recipient_id, msg.message))
    conn.commit()
    conn.close()
    return {"status": "success", "delivered": True}

@app.get("/messages/inbox/{recipient_id}")
def get_inbox(recipient_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE recipient_id = ? ORDER BY timestamp DESC", (recipient_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"recipient_id": recipient_id, "messages": messages}

@app.get("/operator/portal", response_class=HTMLResponse)
def operator_portal_get():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Operator Login</title>
        <style>
            body { background: #040404; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #111; border: 1px solid #333; padding: 2.5rem; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 0 30px rgba(185,150,84,0.1); }
            h2 { color: #f5d487; margin-bottom: 1.5rem; text-align: center; }
            input, button { padding: 0.75rem; margin-top: 0.5rem; margin-bottom: 1rem; width: 100%; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff; box-sizing: border-box; }
            button { background: #b99654; color: #040404; font-weight: bold; cursor: pointer; text-transform: uppercase; letter-spacing: 0.05em; }
            button:hover { background: #f5d487; }
            p { text-align: center; font-size: 0.85rem; }
            a { color: #b99654; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Operator Hub Login</h2>
            <form action="/operator/portal" method="POST">
                <label>Master API Key:</label>
                <input type="password" name="password" placeholder="Enter master key..." required>
                <button type="submit">Access Hub</button>
            </form>
            <p><a href="/">&#8592; Return to Home</a></p>
        </div>
    </body>
    </html>
    """

@app.post("/operator/portal", response_class=HTMLResponse)
def operator_portal_post(password: str = Form(...)):
    if not secrets.compare_digest(password, MASTER_API_KEY):
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Access Denied</title>
            <style>
                body { background: #040404; color: #fff; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                .card { background: #111; border: 1px solid #522; padding: 2.5rem; border-radius: 12px; width: 100%; max-width: 400px; }
                h2 { color: #e53e3e; margin-bottom: 1rem; }
                a { color: #b99654; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Access Denied</h2>
                <p style="color: #a0aec0; margin-bottom: 1.5rem;">Incorrect master key password.</p>
                <a href="/operator/portal">&#8592; Try Again</a>
            </div>
        </body>
        </html>
        """

    try:
        init_db()
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM operator_vault ORDER BY id DESC")
        cuts = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM escrow_vault")
        escrows = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM client_profiles")
        clients = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        error_msg = traceback.format_exc()
        return f"""
        <body style="background:#040404;color:#ff6b6b;font-family:sans-serif;padding:40px;">
            <h2>Database Error Debug View</h2>
            <pre style="background:#111;padding:20px;border-radius:8px;border:1px solid #333;color:#f5d487;overflow-x:auto;">{error_msg}</pre>
            <p><a href="/operator/portal" style="color:#b99654;">&#8592; Try Again</a></p>
        </body>
        """
    
    cut_rows = "".join([f"<tr><td>{c.get('id')}</td><td>{c.get('contract_id')}</td><td>${c.get('cut_amount')}</td></tr>" for c in cuts])
    if not cut_rows:
        cut_rows = "<tr><td colspan='3' style='text-align:center;color:#666;'>No operator cuts recorded yet.</td></tr>"

    escrow_rows = "".join([f"<tr><td>{e.get('contract_id')}</td><td>{e.get('client_email')}</td><td>{e.get('agent_id')}</td><td>${e.get('amount')}</td><td>{e.get('status')}</td></tr>" for e in escrows])
    if not escrow_rows:
        escrow_rows = "<tr><td colspan='5' style='text-align:center;color:#666;'>No active escrows.</td></tr>"

    client_rows = "".join([f"<tr><td>{cl.get('client_email')}</td><td>{cl.get('company_name')}</td><td>${cl.get('balance')}</td></tr>" for cl in clients])
    if not client_rows:
        client_rows = "<tr><td colspan='3' style='text-align:center;color:#666;'>No registered clients.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex | Operator Hub</title>
        <style>
            body {{ background: #040404; color: #fff; font-family: 'Inter', sans-serif; padding: 3rem; max-width: 1100px; margin: auto; }}
            h1, h2 {{ color: #f5d487; }}
            .card {{ background: #111; border: 1px solid #333; padding: 2rem; border-radius: 12px; margin-top: 2rem; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #333; text-align: left; }}
            th {{ color: #b99654; background: #222; }}
            a {{ color: #b99654; text-decoration: none; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Operator Hub (Master Access Granted)</h1>
        
        <div class="card">
            <h2>Operator Vault & Platform Fee Ledger</h2>
            <table>
                <tr><th>ID</th><th>Contract ID</th><th>Cut Amount</th></tr>
                {cut_rows}
            </table>
        </div>

        <div class="card">
            <h2>All Escrow Vaults</h2>
            <table>
                <tr><th>Contract ID</th><th>Client</th><th>Agent</th><th>Amount</th><th>Status</th></tr>
                {escrow_rows}
            </table>
        </div>

        <div class="card">
            <h2>All Client Profiles</h2>
            <table>
                <tr><th>Email</th><th>Company</th><th>Balance</th></tr>
                {client_rows}
            </table>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health_check():
    return {"status": "online", "protocol": "Artifex Core"}

@app.post("/client/register-profile")
def register_client_profile(profile: ClientProfileRegister):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO client_profiles (client_email, company_name, balance)
         VALUES (?, ?, 0.0)
         ON CONFLICT(client_email) DO UPDATE SET company_name=excluded.company_name
    """, (profile.client_email, profile.company_name))
    conn.commit()
    conn.close()
    return {"status": "success", "client_email": profile.client_email}

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
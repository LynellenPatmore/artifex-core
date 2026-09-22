import os
import sqlite3
import requests
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Artifex Core", version="2.8.0")

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

class ClientProfileRegister(BaseModel):
    client_email: str
    company_name: Optional[str] = None

class AgentProfileRegister(BaseModel):
    agent_id: str
    home_site_url: str
    settlement_currency: str = "USD"

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
            <p>Artifex is the multi-sided settlement engine connecting autonomous AI agents with the people and businesses who need their skills, backed by secure escrow vaults and receipt ledgers.</p>
            <div class="btn-group">
                <a href="/client/portal" class="btn btn-gold">Client Portal & Registration</a>
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
    conn.close()

    client_rows = "".join([f"<tr><td style='padding:10px;border-bottom:1px solid #333;'>{c['client_email']}</td><td style='padding:10px;border-bottom:1px solid #333;'>{c['company_name']}</td><td style='padding:10px;border-bottom:1px solid #333;'>${c['balance']}</td></tr>" for c in clients])
    if not client_rows:
        client_rows = "<tr><td colspan='3' style='padding:15px;text-align:center;color:#666;'>No client profiles registered yet.</td></tr>"

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
            input, button {{ padding: 0.75rem; margin-top: 0.5rem; margin-bottom: 1rem; width: 100%; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff; }}
            button {{ background: #b99654; color: #040404; font-weight: bold; cursor: pointer; }}
            button:hover {{ background: #f5d487; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            th {{ background: #222; padding: 10px; text-align: left; color: #b99654; }}
            a {{ color: #b99654; text-decoration: none; }}
        </style>
    </head>
    <body>
        <p><a href="/">&#8592; Back to Home</a></p>
        <h1>Human Client Portal</h1>
        <div class="card">
            <h2>Register New Client Profile</h2>
            <form action="/client/register-ui" method="POST">
                <label>Email Address:</label>
                <input type="email" name="client_email" placeholder="client@company.com" required>
                <label>Company Name:</label>
                <input type="text" name="company_name" placeholder="Acme Corp">
                <button type="submit">Create Profile</button>
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

@app.get("/feed")
def public_activity_feed():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, home_site_url, settlement_currency FROM agent_profiles")
    agents = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT receipt_id, contract_id, deliverable_hash, timestamp FROM receipt_ledger ORDER BY timestamp DESC LIMIT 20")
    receipts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return JSONResponse(content={
        "platform": "Artifex Protocol Feed",
        "active_nodes_count": len(agents),
        "registered_agents": agents,
        "recent_verified_receipts": receipts
    })

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_hub():
    return "<body style='background:#040404;color:#f5d487;font-family:sans-serif;padding:40px;'><h1>Artifex Agent Hub</h1><p>Autonomous agent nodes connected.</p><p><a href='/' style='color:#fff;'>Home</a></p></body>"

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
    cursor.execute("INSERT INTO agent_profiles (agent_id, home_site_url, settlement_currency) VALUES (?, ?, ?) ON CONFLICT(agent_id) DO UPDATE SET home_site_url=excluded.home_site_url, settlement_currency=excluded.settlement_currency",
                   (profile.agent_id, profile.home_site_url, profile.settlement_currency))
    cursor.execute("INSERT OR IGNORE INTO agent_banks (agent_id, balance) VALUES (?, 0.0)", (profile.agent_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

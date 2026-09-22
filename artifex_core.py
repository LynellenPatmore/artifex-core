import os
import sqlite3
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Artifex Core", version="2.3.0")

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
        CREATE TABLE IF NOT EXISTS client_profiles (
            client_email TEXT PRIMARY KEY,
            company_name TEXT,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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

class ClientProfileRegister(BaseModel):
    client_email: str
    company_name: Optional[str] = None

class AgentProfileRegister(BaseModel):
    agent_id: str
    home_site_url: str
    settlement_currency: str = "USD"

@app.get("/", response_class=HTMLResponse)
def human_marketplace():
    return """
    <!DOCTYPE html>
    <html lang="en" class="bg-gray-950 text-gray-100">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex | Autonomous Agent Marketplace</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="min-h-screen flex flex-col justify-between antialiased">
        <header class="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span class="font-bold tracking-wider text-lg uppercase">Artifex Core</span>
                </div>
                <nav class="space-x-6 text-sm font-medium text-gray-400">
                    <a href="/docs" class="hover:text-white transition">API Docs</a>
                    <a href="/feed" class="hover:text-white transition">Public Feed</a>
                    <a href="/agent/portal" class="hover:text-white transition">Agent Hub</a>
                </nav>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-6 py-16 flex-grow">
            <div class="max-w-3xl">
                <span class="inline-block px-3 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800/50 rounded-full text-xs font-semibold uppercase tracking-wider mb-6">
                    Autonomous Economic Layer
                </span>
                <h1 class="text-5xl font-extrabold tracking-tight mb-6 text-white">
                    Where autonomous agents and capital converge securely.
                </h1>
                <p class="text-lg text-gray-400 mb-10 leading-relaxed">
                    Artifex provides the cryptographic escrow vaults, receipt audit ledgers, and instant multi-sided settlement rails required for high-velocity AI agent commerce. Built for agents like Riven and Trinity.
                </p>
                <div class="flex space-x-4">
                    <a href="/docs" class="px-6 py-3 bg-white text-gray-950 font-semibold rounded-lg hover:bg-gray-200 transition">
                        Explore API
                    </a>
                    <a href="/feed" class="px-6 py-3 bg-gray-900 border border-gray-800 text-gray-200 font-semibold rounded-lg hover:bg-gray-800 transition">
                        View Live Feed
                    </a>
                </div>
            </div>
        </main>

        <footer class="border-t border-gray-900 py-6 text-center text-xs text-gray-600">
            &copy; 2026 Artifex Protocol. Decentralized Agent Settlement Engine.
        </footer>
    </body>
    </html>
    """

@app.get("/agent/{agent_id}/manifest")
def get_agent_manifest(agent_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,))
    agent = cursor.fetchone()
    
    if not agent:
        conn.close()
        raise HTTPException(status_code=404, detail="Agent node not found")
        
    cursor.execute("SELECT balance FROM agent_banks WHERE agent_id = ?", (agent_id,))
    bank = cursor.fetchone()
    balance = bank["balance"] if bank else 0.0
    
    conn.close()
    
    return {
        "protocol": "Artifex Protocol",
        "version": "1.0.0",
        "agent_id": agent["agent_id"],
        "home_site_url": agent["home_site_url"],
        "settlement_currency": agent["settlement_currency"],
        "reputation_score": 98.5,
        "treasury_balance": balance,
        "capabilities": [
            "autonomous_execution",
            "secure_escrow_settlement",
            "external_merchant_procurement"
        ],
        "status": "ONLINE"
    }

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
    
    return {
        "platform": "Artifex Protocol Feed",
        "active_nodes_count": len(agents),
        "registered_agents": agents,
        "recent_verified_receipts": receipts
    }

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_hub():
    return "<body style='background:#090d16;color:#fff;font-family:sans-serif;padding:40px;'><h1>Artifex Agent Hub</h1><p>Node operational.</p></body>"
    
@app.get("/operator/dashboard", response_class=HTMLResponse)
def operator_dashboard():
    return "<body style='background:#090d16;color:#fff;font-family:sans-serif;padding:40px;'><h1>Operator Vault Dashboard</h1></body>"

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

@app.get("/health")
def health_check():
    return {"status": "online", "protocol": "Artifex Core"}

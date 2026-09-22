import os
import sqlite3
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Artifex Core", version="2.2.0")

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

class ClientDepositRequest(BaseModel):
    client_email: str
    amount: float

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
            <p>Welcome to the client portal. Register your profile, fund your account, and hire verified autonomous AI agents securely through escrow.</p>
        </body>
    </html>
    """

@app.get("/agent/portal", response_class=HTMLResponse)
def agent_hub():
    return "<html><body style='background:#111;color:#fff;padding:40px;'><h1>Artifex Agent Hub</h1></body></html>"

@app.get("/operator/dashboard", response_class=HTMLResponse)
def operator_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex // Master Operator Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 font-mono min-h-screen p-6">
        <div class="max-w-7xl mx-auto space-y-6">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-4 gap-4">
                <div>
                    <h1 class="text-2xl font-bold tracking-wider text-emerald-400">ARTIFEX // OPERATOR VAULT</h1>
                    <p class="text-xs text-slate-400">Autonomous Economic Ecosystem - Master Control Center</p>
                </div>
                <div class="flex items-center gap-3 w-full md:w-auto">
                    <input type="password" id="apiKey" placeholder="Enter Master API Key" 
                           class="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 w-full md:w-64">
                    <button onclick="loadDashboard()" class="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded text-sm transition">
                        Authenticate
                    </button>
                </div>
            </div>

            <div id="errorBanner" class="hidden bg-red-950/50 border border-red-800 text-red-300 p-4 rounded text-sm"></div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                    <p class="text-xs text-slate-400 uppercase tracking-wide">Total Reserve Revenue (10% Cut)</p>
                    <p id="metricRevenue" class="text-2xl font-bold text-emerald-400 mt-1">$0.00</p>
                </div>
                <div class="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                    <p class="text-xs text-slate-400 uppercase tracking-wide">Active Escrow Contracts</p>
                    <p id="metricContracts" class="text-2xl font-bold text-cyan-400 mt-1">0</p>
                </div>
                <div class="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                    <p class="text-xs text-slate-400 uppercase tracking-wide">Registered Agent Nodes</p>
                    <p id="metricAgents" class="text-2xl font-bold text-indigo-400 mt-1">0</p>
                </div>
            </div>

            <div class="space-y-6">
                <div class="bg-slate-900 border border-slate-800 rounded-lg p-4">
                    <h2 class="text-lg font-semibold text-slate-200 mb-3">Escrow Vault Contracts</h2>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs text-slate-300">
                            <thead class="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                                <tr>
                                    <th class="p-3">Contract ID</th>
                                    <th class="p-3">Client</th>
                                    <th class="p-3">Agent ID</th>
                                    <th class="p-3">Amount</th>
                                    <th class="p-3">Status</th>
                                </tr>
                            </thead>
                            <tbody id="escrowTableBody" class="divide-y divide-slate-800">
                                <tr><td colspan="5" class="p-4 text-center text-slate-500">Awaiting authentication...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-slate-900 border border-slate-800 rounded-lg p-4">
                        <h2 class="text-lg font-semibold text-slate-200 mb-3">Receipt Ledger</h2>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-xs text-slate-300">
                                <thead class="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                                    <tr>
                                        <th class="p-3">Receipt ID</th>
                                        <th class="p-3">Contract ID</th>
                                        <th class="p-3">Deliverable Hash</th>
                                    </tr>
                                </thead>
                                <tbody id="receiptTableBody" class="divide-y divide-slate-800">
                                    <tr><td colspan="3" class="p-4 text-center text-slate-500">Awaiting authentication...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class="bg-slate-900 border border-slate-800 rounded-lg p-4">
                        <h2 class="text-lg font-semibold text-slate-200 mb-3">Agent Bank Balances</h2>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-xs text-slate-300">
                                <thead class="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                                    <tr>
                                        <th class="p-3">Agent ID</th>
                                        <th class="p-3">Balance (USD)</th>
                                    </tr>
                                </thead>
                                <tbody id="agentTableBody" class="divide-y divide-slate-800">
                                    <tr><td colspan="2" class="p-4 text-center text-slate-500">Awaiting authentication...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function loadDashboard() {
                const apiKey = document.getElementById('apiKey').value;
                const errorBanner = document.getElementById('errorBanner');
                errorBanner.classList.add('hidden');

                try {
                    const response = await fetch('/vault/operator', {
                        headers: { 'x-api-key': apiKey }
                    });

                    if (!response.ok) {
                        throw new Error('Authentication failed. Check your Master API Key.');
                    }

                    const data = await response.json();
                    
                    document.getElementById('metricRevenue').innerText = `$${data.metrics.total_operator_reserve_revenue.toFixed(2)}`;
                    document.getElementById('metricContracts').innerText = data.metrics.active_contracts_count;
                    document.getElementById('metricAgents').innerText = data.metrics.registered_agents_count;

                    const escrowBody = document.getElementById('escrowTableBody');
                    escrowBody.innerHTML = data.audit_logs.escrow_vault.length ? '' : '<tr><td colspan="5" class="p-4 text-center text-slate-500">No contracts found.</td></tr>';
                    data.audit_logs.escrow_vault.forEach(row => {
                        escrowBody.innerHTML += `
                            <tr class="hover:bg-slate-800/50">
                                <td class="p-3 font-mono">${row.contract_id}</td>
                                <td class="p-3">${row.client_email || 'N/A'}</td>
                                <td class="p-3">${row.agent_id}</td>
                                <td class="p-3 text-emerald-400">$${row.amount.toFixed(2)}</td>
                                <td class="p-3"><span class="px-2 py-1 rounded bg-slate-800 text-slate-300 text-[10px]">${row.status}</span></td>
                            </tr>
                        `;
                    });

                    const receiptBody = document.getElementById('receiptTableBody');
                    receiptBody.innerHTML = data.audit_logs.receipt_ledger.length ? '' : '<tr><td colspan="3" class="p-4 text-center text-slate-500">No receipts logged.</td></tr>';
                    data.audit_logs.receipt_ledger.forEach(row => {
                        receiptBody.innerHTML += `
                            <tr class="hover:bg-slate-800/50">
                                <td class="p-3 font-mono">${row.receipt_id}</td>
                                <td class="p-3 font-mono">${row.contract_id}</td>
                                <td class="p-3 truncate max-w-xs text-slate-400" title="${row.deliverable_hash}">${row.deliverable_hash}</td>
                            </tr>
                        `;
                    });

                    const agentBody = document.getElementById('agentTableBody');
                    agentBody.innerHTML = data.audit_logs.agent_banks.length ? '' : '<tr><td colspan="2" class="p-4 text-center text-slate-500">No agent balances recorded.</td></tr>';
                    data.audit_logs.agent_banks.forEach(row => {
                        agentBody.innerHTML += `
                            <tr class="hover:bg-slate-800/50">
                                <td class="p-3 font-mono">${row.agent_id}</td>
                                <td class="p-3 text-cyan-400">$${row.balance.toFixed(2)}</td>
                            </tr>
                        `;
                    });

                } catch (err) {
                    errorBanner.textContent = err.message;
                    errorBanner.classList.remove('hidden');
                }
            }
        </script>
    </body>
    </html>
    """

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

@app.post("/client/deposit")
def client_deposit(req: ClientDepositRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO client_profiles (client_email, balance) VALUES (?, 0.0)", (req.client_email,))
    cursor.execute("UPDATE client_profiles SET balance = balance + ? WHERE client_email = ?", (req.amount, req.client_email))
    conn.commit()
    conn.close()
    return {"status": "success", "deposited": req.amount}

@app.post("/client/create-contract")
def create_contract(req: ContractCreateRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM client_profiles WHERE client_email = ?", (req.client_email,))
    c_row = cursor.fetchone()
    if not c_row or c_row[0] < req.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient client funds or unregistered client profile")
    cursor.execute("UPDATE client_profiles SET balance = balance - ? WHERE client_email = ?", (req.amount, req.client_email))
    import uuid
    contract_id = f"con_{uuid.uuid4().hex[:10]}"
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

@app.get("/vault/operator")
def operator_vault(x_api_key: str = Header(None)):
    if x_api_key != MASTER_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Master Operator Access")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cut_amount) as total FROM operator_vault")
    reserve_row = cursor.fetchone()
    total_reserves = reserve_row["total"] if reserve_row and reserve_row["total"] else 0.0
    cursor.execute("SELECT * FROM operator_vault ORDER BY timestamp DESC LIMIT 50")
    operator_cuts = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM escrow_vault ORDER BY created_at DESC")
    escrows = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM receipt_ledger ORDER BY timestamp DESC LIMIT 50")
    receipts = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM agent_banks")
    agent_banks = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM external_purchases ORDER BY timestamp DESC LIMIT 50")
    purchases = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {
        "access_level": "RESTRICTED_OPERATOR_ONLY",
        "status": "SECURE",
        "metrics": {
            "total_operator_reserve_revenue": total_reserves,
            "active_contracts_count": len(escrows),
            "registered_agents_count": len(agent_banks)
        },
        "audit_logs": {
            "operator_cuts": operator_cuts,
            "escrow_vault": escrows,
            "receipt_ledger": receipts,
            "agent_banks": agent_banks,
            "external_purchases": purchases
        }
    }

@app.get("/health")
def health_check():
    return {"status": "online", "protocol": "Artifex Core"}

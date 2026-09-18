import hashlib
import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

DB_FILE = os.getenv("DB_FILE", "artifex.db")

# --- Security & Auth Configuration ---
API_KEY = os.getenv("API_KEY", "artifex_secret_key_123")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key


# --- Database Setup & Initialization ---
def init_sqlite_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance REAL NOT NULL
        );
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS escrow_vault (
            contract_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            primary_agent_id TEXT NOT NULL,
            guarantor_id TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL
        );
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS receipt_ledger (
            receipt_id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            timestamp_utc TEXT DEFAULT CURRENT_TIMESTAMP,
            deliverable_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            audit_trail_signature TEXT NOT NULL,
            correction_note TEXT
        );
    """
    )

    cursor.execute("SELECT COUNT(*) FROM accounts;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO accounts (account_id, balance) VALUES (?, ?);",
            [
                ("client_lyn", 150.0),
                ("agent_riven", 0.0),
                ("guarantor_node", 0.0),
            ],
        )

    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_sqlite_db()
    yield


app = FastAPI(
    title="Artifex Protocol API",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Data Models ---
class ContractCreateRequest(BaseModel):
    client_id: str
    primary_agent_id: str
    amount: float
    guarantor_id: str = "guarantor_node"


class ContractSettleRequest(BaseModel):
    contract_id: str
    deliverable_data: str
    is_verified: bool


class ContractCancelRequest(BaseModel):
    contract_id: str
    client_id: str
    reason: str


class WithdrawRequest(BaseModel):
    agent_id: str
    amount: float
    destination_type: str
    destination_address: str
    memo: Optional[str] = None


class FiatDepositRequest(BaseModel):
    client_id: str
    amount: float
    provider: str
    external_tx_id: str


# --- Public Endpoints ---
@app.get("/")
def read_root():
    return {"status": "Artifex Protocol Online (SQLite Persistence Active)"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/balances")
def get_balances():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT account_id, balance FROM accounts;")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


@app.get("/manifest/{agent_id}")
def get_manifest(agent_id: str):
    return {
        "agent_id": agent_id,
        "protocol": "Artifex Escrow v1",
        "supported_methods": ["SHA-256"],
    }


@app.get("/receipt/verify/{receipt_id}")
def verify_receipt(receipt_id: str):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT receipt_id, contract_id, agent_id, timestamp_utc, deliverable_hash, status, audit_trail_signature, correction_note 
            FROM receipt_ledger 
            WHERE receipt_id = ?
            """,
            (receipt_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Receipt not found.")

        (
            rcpt_id,
            contract_id,
            agent_id,
            timestamp,
            deliverable_hash,
            status,
            stored_signature,
            correction_note,
        ) = row

        expected_payload = (
            f"{contract_id}:{agent_id}:{deliverable_hash}:{status}:{timestamp}"
        )
        computed_signature = hashlib.sha256(
            expected_payload.encode("utf-8")
        ).hexdigest()

        return {
            "receipt_id": rcpt_id,
            "contract_id": contract_id,
            "agent_id": agent_id,
            "status": status,
            "timestamp_utc": timestamp,
            "deliverable_hash": deliverable_hash,
            "verification": {
                "cryptographically_valid": computed_signature
                == stored_signature,
                "audit_signature": stored_signature,
            },
            "correction_note": correction_note,
        }
    finally:
        conn.close()


@app.get("/agent/profile/{agent_id}")
def get_agent_profile(agent_id: str):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_id = ?", (agent_id,)
        )
        agent_acc = cursor.fetchone()
        if not agent_acc:
            raise HTTPException(status_code=404, detail="Agent profile not found.")

        cursor.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(amount), 0.0) 
            FROM escrow_vault 
            WHERE primary_agent_id = ? AND status = 'SETTLED'
            """,
            (agent_id,),
        )
        completed_count, total_volume = cursor.fetchone()

        cursor.execute(
            """
            SELECT receipt_id, contract_id, timestamp_utc, audit_trail_signature 
            FROM receipt_ledger 
            WHERE agent_id = ? AND status = 'VERIFIED_SUCCESS'
            ORDER BY timestamp_utc DESC
            """,
            (agent_id,),
        )
        receipt_rows = cursor.fetchall()

        verified_receipts = [
            {
                "receipt_id": r[0],
                "contract_id": r[1],
                "timestamp_utc": r[2],
                "audit_signature": r[3],
            }
            for r in receipt_rows
        ]

        return {
            "agent_id": agent_id,
            "current_balance": agent_acc[0],
            "trust_metrics": {
                "completed_contracts": completed_count,
                "verified_volume_escrow": total_volume,
                "primary_payout_earned": total_volume * 0.70,
            },
            "verified_receipts": verified_receipts,
        }
    finally:
        conn.close()


# --- Protected Protocol Endpoints ---
@app.post("/contract/create", dependencies=[Security(verify_api_key)])
def create_contract(req: ContractCreateRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (req.client_id,)
    )
    row = cursor.fetchone()

    if not row or row[0] < req.amount:
        conn.close()
        raise HTTPException(
            status_code=400, detail="Insufficient client funds."
        )

    cursor.execute(
        "UPDATE accounts SET balance = balance - ? WHERE account_id = ?",
        (req.amount, req.client_id),
    )

    contract_id = f"cnt_{hashlib.sha256(f'{req.client_id}:{req.amount}'.encode()).hexdigest()[:8]}"
    cursor.execute(
        """
        INSERT INTO escrow_vault (contract_id, client_id, primary_agent_id, guarantor_id, amount, status)
        VALUES (?, ?, ?, ?, ?, 'LOCKED');
    """,
        (
            contract_id,
            req.client_id,
            req.primary_agent_id,
            req.guarantor_id,
            req.amount,
        ),
    )

    conn.commit()
    conn.close()
    return {
        "status": "ESCROW_LOCKED",
        "contract_id": contract_id,
        "amount": req.amount,
    }


@app.post("/contract/settle", dependencies=[Security(verify_api_key)])
def settle_contract(req: ContractSettleRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT client_id, primary_agent_id, guarantor_id, amount, status FROM escrow_vault WHERE contract_id = ?",
        (req.contract_id,),
    )
    row = cursor.fetchone()

    if not row or row[4] != "LOCKED":
        conn.close()
        raise HTTPException(
            status_code=400, detail="Contract not found or already settled."
        )

    _, primary_agent, guarantor, amount, _ = row

    if not req.is_verified:
        cursor.execute(
            "UPDATE escrow_vault SET status = 'FAILED' WHERE contract_id = ?",
            (req.contract_id,),
        )
        conn.commit()
        conn.close()
        return {"status": "SETTLEMENT_FAILED"}

    primary_payout = amount * 0.70
    guarantor_payout = amount * 0.30

    cursor.execute(
        "UPDATE accounts SET balance = balance + ? WHERE account_id = ?",
        (primary_payout, primary_agent),
    )
    cursor.execute(
        "UPDATE accounts SET balance = balance + ? WHERE account_id = ?",
        (guarantor_payout, guarantor),
    )
    cursor.execute(
        "UPDATE escrow_vault SET status = 'SETTLED' WHERE contract_id = ?",
        (req.contract_id,),
    )

    deliv_hash = hashlib.sha256(
        req.deliverable_data.encode("utf-8")
    ).hexdigest()
    receipt_id = f"rcpt_{deliv_hash[:8]}"
    timestamp = "2026-09-18T10:00:00Z"
    status_str = "VERIFIED_SUCCESS"

    payload_str = (
        f"{req.contract_id}:{primary_agent}:{deliv_hash}:{status_str}:{timestamp}"
    )
    signature = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    cursor.execute(
        """
        INSERT INTO receipt_ledger 
        (receipt_id, contract_id, agent_id, timestamp_utc, deliverable_hash, status, audit_trail_signature, correction_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL);
    """,
        (
            receipt_id,
            req.contract_id,
            primary_agent,
            timestamp,
            deliv_hash,
            status_str,
            signature,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "status": status_str,
        "receipt_id": receipt_id,
        "audit_signature": signature,
    }


@app.post("/contract/cancel", dependencies=[Security(verify_api_key)])
def cancel_contract(req: ContractCancelRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT client_id, amount, status FROM escrow_vault WHERE contract_id = ?",
        (req.contract_id,),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Contract not found.")

    client_id, amount, status_str = row

    if client_id != req.client_id:
        conn.close()
        raise HTTPException(
            status_code=403, detail="Unauthorized client for this contract."
        )

    if status_str != "LOCKED":
        conn.close()
        raise HTTPException(
            status_code=400, detail="Only LOCKED contracts can be cancelled."
        )

    cursor.execute(
        "UPDATE accounts SET balance = balance + ? WHERE account_id = ?",
        (amount, req.client_id),
    )

    cursor.execute(
        "UPDATE escrow_vault SET status = 'CANCELLED' WHERE contract_id = ?",
        (req.contract_id,),
    )

    conn.commit()
    conn.close()

    return {
        "status": "ESCROW_REFUNDED",
        "contract_id": req.contract_id,
        "refunded_amount": amount,
        "reason": req.reason,
    }


@app.post("/agent/withdraw", dependencies=[Security(verify_api_key)])
def withdraw_funds(req: WithdrawRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (req.agent_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Agent account not found.")

    current_balance = row[0]
    if current_balance < req.amount:
        conn.close()
        raise HTTPException(
            status_code=400, detail="Insufficient agent funds for withdrawal."
        )

    cursor.execute(
        "UPDATE accounts SET balance = balance - ? WHERE account_id = ?",
        (req.amount, req.agent_id),
    )

    conn.commit()
    conn.close()

    tx_id = f"tx_{hashlib.sha256(f'{req.agent_id}:{req.amount}:{req.destination_address}'.encode()).hexdigest()[:8]}"

    return {
        "status": "WITHDRAWAL_SUCCESSFUL",
        "tx_id": tx_id,
        "agent_id": req.agent_id,
        "amount_deducted": req.amount,
        "remaining_balance": current_balance - req.amount,
        "destination": {
            "type": req.destination_type,
            "target": req.destination_address,
        },
        "memo": req.memo,
    }


@app.post("/deposit/fiat", dependencies=[Security(verify_api_key)])
def deposit_fiat(req: FiatDepositRequest):
    if req.amount <= 0:
        raise HTTPException(
            status_code=400, detail="Deposit amount must be greater than zero."
        )

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (req.client_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Client account not found.")

    current_balance = row[0]
    new_balance = current_balance + req.amount

    cursor.execute(
        "UPDATE accounts SET balance = ? WHERE account_id = ?",
        (new_balance, req.client_id),
    )

    conn.commit()
    conn.close()

    deposit_receipt_id = f"dep_{hashlib.sha256(f'{req.external_tx_id}:{req.client_id}'.encode()).hexdigest()[:8]}"

    return {
        "status": "DEPOSIT_SUCCESSFUL",
        "deposit_receipt_id": deposit_receipt_id,
        "client_id": req.client_id,
        "amount_credited": req.amount,
        "new_balance": new_balance,
        "provider_info": {
            "gateway": req.provider,
            "external_tx_id": req.external_tx_id,
        },
    }
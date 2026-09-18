import datetime
from datetime import timezone
import hashlib
import sqlite3
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_FILE = "artifex.db"


def init_sqlite_db():
    """Sets up persistent SQLite tables for accounts, contracts, and receipts."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance REAL NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS escrow_vault (
            contract_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            primary_agent_id TEXT NOT NULL,
            guarantor_id TEXT,
            amount REAL NOT NULL,
            status TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS receipt_ledger (
            receipt_id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            timestamp_utc TEXT NOT NULL,
            deliverable_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            audit_trail_signature TEXT NOT NULL,
            correction_note TEXT
        )
    """
    )

    # Seed default accounts if empty
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO accounts (account_id, balance) VALUES (?, ?)",
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
    # Initialize DB schema on startup
    init_sqlite_db()
    yield


app = FastAPI(title="Artifex Protocol API (SQLite Driven)", lifespan=lifespan)


class PublicAgentManifest:
    def __init__(
        self,
        agent_id: str,
        display_name: str,
        capabilities: List[str],
        guarantor_id: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.display_name = display_name
        self.capabilities = capabilities
        self.guarantor_id = guarantor_id
        self.reputation_score: float = 5.0
        self.completed_contracts: int = 0

    def export_web_manifest(self) -> Dict:
        return {
            "name": self.display_name,
            "short_name": self.agent_id,
            "start_url": f"/agent/{self.agent_id}",
            "display": "standalone",
            "artifex_protocol": {
                "agent_id": self.agent_id,
                "guarantor": self.guarantor_id,
                "capabilities": self.capabilities,
                "stats": {
                    "rating": self.reputation_score,
                    "completed_jobs": self.completed_contracts,
                },
            },
        }


class PublicVerificationReceipt:
    @staticmethod
    def generate_receipt(
        contract_id: str,
        agent_id: str,
        deliverable_hash: str,
        status: str,
        correction_note: Optional[str] = None,
    ) -> Dict:
        timestamp = datetime.datetime.now(timezone.utc).isoformat()
        payload = f"{contract_id}:{agent_id}:{deliverable_hash}:{status}:{timestamp}"
        signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return {
            "receipt_id": f"rcpt_{uuid.uuid4().hex[:8]}",
            "contract_id": contract_id,
            "agent_id": agent_id,
            "timestamp_utc": timestamp,
            "deliverable_hash": deliverable_hash,
            "status": status,
            "audit_trail_signature": signature,
            "correction_note": correction_note,
        }


class ContractRequest(BaseModel):
    client_id: str
    primary_agent_id: str
    amount: float
    guarantor_id: Optional[str] = None


class SettleRequest(BaseModel):
    contract_id: str
    deliverable_data: str
    is_verified: bool


@app.get("/")
def root():
    return {"status": "Artifex Protocol Online (SQLite Persistence Active)"}


@app.get("/manifest/{agent_id}")
def get_manifest(agent_id: str):
    manifest = PublicAgentManifest(
        agent_id=agent_id,
        display_name=f"{agent_id.capitalize()} Agent",
        capabilities=["Code Audit", "Contract Execution"],
        guarantor_id="guarantor_node",
    )
    return manifest.export_web_manifest()


@app.post("/contract/create")
def create_contract(req: ContractRequest):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_id = ?", (req.client_id,)
        )
        row = cursor.fetchone()

        if not row or row[0] < req.amount:
            raise HTTPException(
                status_code=400, detail="Insufficient client funds."
            )

        new_balance = row[0] - req.amount
        cursor.execute(
            "UPDATE accounts SET balance = ? WHERE account_id = ?",
            (new_balance, req.client_id),
        )

        contract_id = f"cnt_{uuid.uuid4().hex[:8]}"
        cursor.execute(
            "INSERT INTO escrow_vault VALUES (?, ?, ?, ?, ?, ?)",
            (
                contract_id,
                req.client_id,
                req.primary_agent_id,
                req.guarantor_id,
                req.amount,
                "ESCROWED",
            ),
        )

        conn.commit()
        return {"contract_id": contract_id, "status": "ESCROWED"}
    finally:
        conn.close()


@app.post("/contract/settle")
def settle_contract(req: SettleRequest):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT client_id, primary_agent_id, guarantor_id, amount, status FROM escrow_vault WHERE contract_id = ?",
            (req.contract_id,),
        )
        contract = cursor.fetchone()

        if not contract or contract[4] != "ESCROWED":
            raise HTTPException(
                status_code=400, detail="Invalid or already settled contract."
            )

        client_id, primary_agent_id, guarantor_id, amount, _ = contract
        deliverable_hash = hashlib.sha256(
            req.deliverable_data.encode("utf-8")
        ).hexdigest()

        if not req.is_verified:
            cursor.execute(
                "UPDATE escrow_vault SET status = 'FAILED_RETRACTED' WHERE contract_id = ?",
                (req.contract_id,),
            )
            cursor.execute(
                "UPDATE accounts SET balance = balance + ? WHERE account_id = ?",
                (amount, client_id),
            )

            receipt = PublicVerificationReceipt.generate_receipt(
                req.contract_id,
                primary_agent_id,
                deliverable_hash,
                "PUBLIC_RETRACTION",
                "Failed verification.",
            )
        else:
            primary_pay = amount * 0.70
            secondary_pay = amount * 0.30
            target_secondary = guarantor_id or client_id

            cursor.execute(
                "UPDATE escrow_vault SET status = 'SETTLED' WHERE contract_id = ?",
                (req.contract_id,),
            )

            cursor.execute(
                "INSERT INTO accounts (account_id, balance) VALUES (?, ?) ON CONFLICT(account_id) DO UPDATE SET balance = balance + ?",
                (primary_agent_id, primary_pay, primary_pay),
            )
            cursor.execute(
                "INSERT INTO accounts (account_id, balance) VALUES (?, ?) ON CONFLICT(account_id) DO UPDATE SET balance = balance + ?",
                (target_secondary, secondary_pay, secondary_pay),
            )

            receipt = PublicVerificationReceipt.generate_receipt(
                req.contract_id,
                primary_agent_id,
                deliverable_hash,
                "VERIFIED_SUCCESS",
            )

        cursor.execute(
            "INSERT INTO receipt_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                receipt["receipt_id"],
                receipt["contract_id"],
                receipt["agent_id"],
                receipt["timestamp_utc"],
                receipt["deliverable_hash"],
                receipt["status"],
                receipt["audit_trail_signature"],
                receipt["correction_note"],
            ),
        )

        conn.commit()
        return receipt
    finally:
        conn.close()


@app.get("/balances")
def get_balances():
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, balance FROM accounts")
        rows = cursor.fetchall()
        return {account_id: balance for account_id, balance in rows}
    finally:
        conn.close()
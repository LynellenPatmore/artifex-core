import sqlite3
import os

DB_PATH = os.getenv('DB_PATH', 'artifex.db')

def get_db():
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_db()
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS escrow_vault (
        contract_id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        client_id TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipt_ledger (
        receipt_id TEXT PRIMARY KEY,
        contract_id TEXT NOT NULL,
        deliverable_hash TEXT NOT NULL,
        audit_signature TEXT NOT NULL,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contract_id) REFERENCES escrow_vault (contract_id)
    )
''')
conn.commit()
conn.close()

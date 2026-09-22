import urllib.request
import json

headers = {
    "Content-Type": "application/json",
    "x-api-key": "artifex-master-secure-key-1997"
}

# 1. Create Escrow Contract
print("--- Creating Escrow ---")
escrow_url = "http://127.0.0.1:8000/api/v1/escrow"
escrow_data = {
    "agent_id": "agent_alpha",
    "client_id": "client_one",
    "amount": 100.0
}
req = urllib.request.Request(escrow_url, data=json.dumps(escrow_data).encode("utf-8"), headers=headers, method="POST")
with urllib.request.urlopen(req) as response:
    res_json = json.loads(response.read().decode())
    contract_id = res_json.get("contract_id")
    print(f"Success! Contract ID: {contract_id}")

# 2. Create Receipt using the dynamic contract ID
print(f"\n--- Creating Receipt for {contract_id} ---")
receipt_url = "http://127.0.0.1:8000/api/v1/receipts"
receipt_data = {
    "receipt_id": "rec_001",
    "contract_id": contract_id,
    "deliverable_hash": "sha256_mock_hash_abc123",
    "status": "verified",
    "audit_signature": "mock_signature_sig789"
}
req = urllib.request.Request(receipt_url, data=json.dumps(receipt_data).encode("utf-8"), headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as response:
        print("Receipt Result:", response.read().decode())
except Exception as e:
    print("Receipt Error:", e.read().decode() if hasattr(e, 'read') else e)

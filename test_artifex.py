import pytest
from fastapi.testclient import TestClient
from artifex_core import app, MASTER_API_KEY, DB_FILE
import sqlite3

client = TestClient(app)

def test_home_route():
    response = client.get('/')
    assert response.status_code == 200
    assert b'Artifex Human Marketplace' in response.content

def test_health_route():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_unauthorized_master_reserve():
    assert client.get('/vault/operator').status_code == 401

def test_authorized_master_reserve_audit():
    headers = {"x-api-key": MASTER_API_KEY}
    res = client.get('/vault/operator', headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data['access_level'] == "RESTRICTED_OPERATOR_ONLY"
    assert "metrics" in data
    assert "audit_logs" in data
    assert "operator_cuts" in data["audit_logs"]
    assert "escrow_vault" in data["audit_logs"]

def test_client_workflow():
    c_res = client.post("/client/create-contract", json={"client_email": "test@test.com", "agent_id": "a1", "amount": 100.0})
    assert c_res.status_code == 200
    cid = c_res.json()["contract_id"]
    a_res = client.post("/client/approve-work", json={"contract_id": cid, "deliverable_hash": "abc", "audit_signature": "sig"})
    assert a_res.status_code == 200
    assert a_res.json()["operator_reserve_cut"] == 10.0

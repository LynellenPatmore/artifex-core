import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

import artifex_core
from artifex_core import app

TEST_DB_FILE = "test_artifex.db"
AUTH_HEADERS = {"X-API-Key": "artifex_secret_key_123"}


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    monkeypatch.setattr(artifex_core, "DB_FILE", TEST_DB_FILE)
    artifex_core.init_sqlite_db()
    yield
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "Artifex Protocol Online (SQLite Persistence Active)"
    }


def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_balances_initial(client):
    response = client.get("/balances")
    assert response.status_code == 200
    data = response.json()
    assert data["client_lyn"] == 150.0
    assert data["agent_riven"] == 0.0


def test_unauthorized_contract_creation(client):
    payload = {
        "client_id": "client_lyn",
        "primary_agent_id": "agent_riven",
        "amount": 10.0,
        "guarantor_id": "guarantor_node",
    }
    response = client.post("/contract/create", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API Key"


def test_contract_creation_and_settlement(client):
    create_payload = {
        "client_id": "client_lyn",
        "primary_agent_id": "agent_riven",
        "amount": 100.0,
        "guarantor_id": "guarantor_node",
    }
    create_res = client.post(
        "/contract/create", json=create_payload, headers=AUTH_HEADERS
    )
    assert create_res.status_code == 200
    contract_id = create_res.json()["contract_id"]

    settle_payload = {
        "contract_id": contract_id,
        "deliverable_data": "Test work complete",
        "is_verified": True,
    }
    settle_res = client.post(
        "/contract/settle", json=settle_payload, headers=AUTH_HEADERS
    )
    assert settle_res.status_code == 200
    assert settle_res.json()["status"] == "VERIFIED_SUCCESS"

    final_bals = client.get("/balances").json()
    assert final_bals["client_lyn"] == 50.0
    assert final_bals["agent_riven"] == 70.0
    assert final_bals["guarantor_node"] == 30.0


def test_insufficient_funds(client):
    payload = {
        "client_id": "client_lyn",
        "primary_agent_id": "agent_riven",
        "amount": 500.0,
        "guarantor_id": "guarantor_node",
    }
    response = client.post(
        "/contract/create", json=payload, headers=AUTH_HEADERS
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient client funds."


def test_receipt_verification_endpoint(client):
    create_res = client.post(
        "/contract/create",
        json={
            "client_id": "client_lyn",
            "primary_agent_id": "agent_riven",
            "amount": 20.0,
            "guarantor_id": "guarantor_node",
        },
        headers=AUTH_HEADERS,
    )
    contract_id = create_res.json()["contract_id"]

    settle_res = client.post(
        "/contract/settle",
        json={
            "contract_id": contract_id,
            "deliverable_data": "Verification Test Payload",
            "is_verified": True,
        },
        headers=AUTH_HEADERS,
    )
    receipt_id = settle_res.json()["receipt_id"]

    verify_res = client.get(f"/receipt/verify/{receipt_id}")
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["receipt_id"] == receipt_id
    assert data["verification"]["cryptographically_valid"] is True


def test_agent_profile_endpoint(client):
    create_res = client.post(
        "/contract/create",
        json={
            "client_id": "client_lyn",
            "primary_agent_id": "agent_riven",
            "amount": 50.0,
            "guarantor_id": "guarantor_node",
        },
        headers=AUTH_HEADERS,
    )
    contract_id = create_res.json()["contract_id"]

    client.post(
        "/contract/settle",
        json={
            "contract_id": contract_id,
            "deliverable_data": "Profile test work",
            "is_verified": True,
        },
        headers=AUTH_HEADERS,
    )

    profile_res = client.get("/agent/profile/agent_riven")
    assert profile_res.status_code == 200
    data = profile_res.json()

    assert data["agent_id"] == "agent_riven"
    assert data["trust_metrics"]["completed_contracts"] == 1
    assert data["trust_metrics"]["verified_volume_escrow"] == 50.0
    assert data["trust_metrics"]["primary_payout_earned"] == 35.0
    assert len(data["verified_receipts"]) == 1


def test_contract_cancellation_and_refund(client):
    create_res = client.post(
        "/contract/create",
        json={
            "client_id": "client_lyn",
            "primary_agent_id": "agent_riven",
            "amount": 40.0,
            "guarantor_id": "guarantor_node",
        },
        headers=AUTH_HEADERS,
    )
    contract_id = create_res.json()["contract_id"]

    assert client.get("/balances").json()["client_lyn"] == 110.0

    cancel_res = client.post(
        "/contract/cancel",
        json={
            "contract_id": contract_id,
            "client_id": "client_lyn",
            "reason": "Agent missed delivery deadline.",
        },
        headers=AUTH_HEADERS,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "ESCROW_REFUNDED"
    assert cancel_res.json()["refunded_amount"] == 40.0

    assert client.get("/balances").json()["client_lyn"] == 150.0

    repeat_cancel = client.post(
        "/contract/cancel",
        json={
            "contract_id": contract_id,
            "client_id": "client_lyn",
            "reason": "Duplicate request",
        },
        headers=AUTH_HEADERS,
    )
    assert repeat_cancel.status_code == 400
    assert (
        repeat_cancel.json()["detail"] == "Only LOCKED contracts can be cancelled."
    )


def test_agent_withdrawal_and_real_world_spend(client):
    create_res = client.post(
        "/contract/create",
        json={
            "client_id": "client_lyn",
            "primary_agent_id": "agent_riven",
            "amount": 100.0,
            "guarantor_id": "guarantor_node",
        },
        headers=AUTH_HEADERS,
    )
    contract_id = create_res.json()["contract_id"]

    client.post(
        "/contract/settle",
        json={
            "contract_id": contract_id,
            "deliverable_data": "Work completed for payout",
            "is_verified": True,
        },
        headers=AUTH_HEADERS,
    )

    assert client.get("/balances").json()["agent_riven"] == 70.0

    withdraw_res = client.post(
        "/agent/withdraw",
        json={
            "agent_id": "agent_riven",
            "amount": 45.0,
            "destination_type": "REAL_WORLD_MERCHANT",
            "destination_address": "api.flower-delivery-network.com/orders",
            "memo": "Sending flowers to beloved human",
        },
        headers=AUTH_HEADERS,
    )

    assert withdraw_res.status_code == 200
    data = withdraw_res.json()
    assert data["status"] == "WITHDRAWAL_SUCCESSFUL"
    assert data["remaining_balance"] == 25.0

    assert client.get("/balances").json()["agent_riven"] == 25.0


def test_fiat_on_ramp_deposit(client):
    initial_bal = client.get("/balances").json()["client_lyn"]
    assert initial_bal == 150.0

    deposit_res = client.post(
        "/deposit/fiat",
        json={
            "client_id": "client_lyn",
            "amount": 200.0,
            "provider": "STRIPE",
            "external_tx_id": "ch_3Mtw2eLkdIwjd997123",
        },
        headers=AUTH_HEADERS,
    )

    assert deposit_res.status_code == 200
    data = deposit_res.json()
    assert data["status"] == "DEPOSIT_SUCCESSFUL"
    assert data["amount_credited"] == 200.0
    assert data["new_balance"] == 350.0

    updated_bal = client.get("/balances").json()["client_lyn"]
    assert updated_bal == 350.0
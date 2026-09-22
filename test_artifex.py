import pytest
from fastapi.testclient import TestClient
from artifex_core import app, MASTER_API_KEY

client = TestClient(app)

def test_home_route():
    response = client.get('/')
    assert response.status_code == 200
    assert b'ARTIFEX' in response.content

def test_health_route():
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_unauthorized_master_reserve():
    res = client.get('/vault/operator')
    assert res.status_code == 401

def test_authorized_master_reserve():
    headers = {"x-api-key": MASTER_API_KEY}
    res = client.get('/vault/operator', headers=headers)
    assert res.status_code == 200
    assert res.json()['access_level'] == "RESTRICTED_OPERATOR_ONLY"

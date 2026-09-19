import pytest
from artifex_core import app, db, Record, API_KEY

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Artifex Dashboard' in response.data

def test_health_route(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok"}

def test_unauthorized_access(client):
    res = client.post('/records', json={"name": "Hacker Artifact"})
    assert res.status_code == 401

def test_crud_records_with_auth(client):
    headers = {"X-API-Key": API_KEY}

    res = client.get('/records')
    assert res.status_code == 200
    assert res.json == []

    res = client.post('/records', json={"name": "Test Artifact"}, headers=headers)
    assert res.status_code == 201
    data = res.json
    assert data['name'] == "Test Artifact"
    record_id = data['id']

    res = client.put(f'/records/{record_id}', json={"name": "Updated Artifact"}, headers=headers)
    assert res.status_code == 200
    assert res.json['name'] == "Updated Artifact"

    res = client.delete(f'/records/{record_id}', headers=headers)
    assert res.status_code == 200
    assert "deleted successfully" in res.json['message']

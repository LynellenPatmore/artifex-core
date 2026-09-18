import pytest
from artifex_core import app, db, Record

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

def test_crud_records(client):
    # 1. Test empty records list
    res = client.get('/records')
    assert res.status_code == 200
    assert res.json == []

    # 2. Test creating a record (POST)
    res = client.post('/records', json={"name": "Test Artifact"})
    assert res.status_code == 201
    data = res.json
    assert data['name'] == "Test Artifact"
    record_id = data['id']

    # 3. Test reading records list again
    res = client.get('/records')
    assert res.status_code == 200
    assert len(res.json) == 1

    # 4. Test updating the record (PUT)
    res = client.put(f'/records/{record_id}', json={"name": "Updated Artifact"})
    assert res.status_code == 200
    assert res.json['name'] == "Updated Artifact"

    # 5. Test deleting the record (DELETE)
    res = client.delete(f'/records/{record_id}')
    assert res.status_code == 200
    assert "deleted successfully" in res.json['message']

    # 6. Verify record is gone
    res = client.get('/records')
    assert res.json == []

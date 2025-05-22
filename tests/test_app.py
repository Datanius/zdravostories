import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_lists_stories(client):
    resp = client.get('/')
    assert resp.status_code == 200
    # Should contain at least one known story
    assert b'evening_at_a_bar' in resp.data

def test_story_page(client):
    resp = client.get('/story/bosnian/evening_at_a_bar')
    assert resp.status_code == 200
    assert b'Evening at a Bar' in resp.data

import json
from unittest.mock import Mock, patch

import pytest
from src.main import create_app
from src.models.user import db


@pytest.fixture
def client(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "test.db"}'})
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.session.remove()


def test_notes_crud_and_validation(client):
    assert client.get('/api/health').json == {'status': 'ok'}
    assert client.post('/api/notes', json={'title': '', 'content': ''}).status_code == 400
    response = client.post('/api/notes', json={'title': 'Idea', 'content': 'A useful thought'})
    assert response.status_code == 201
    note_id = response.json['id']
    assert len(client.get('/api/notes?q=useful').json) == 1
    assert client.get('/api/notes/search?q=missing').json == []
    assert client.put(f'/api/notes/{note_id}', json={'title': 'Revised', 'content': 'Body'}).json['title'] == 'Revised'
    assert client.delete(f'/api/notes/{note_id}').status_code == 204
    assert client.get(f'/api/notes/{note_id}').status_code == 404
    assert client.put('/api/notes/99', json={'title': 'X', 'content': 'Y'}).status_code == 404


def test_translation_success_and_input_errors(client, monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    mock_response = Mock()
    mock_response.json.return_value = {'choices': [{'message': {'content': json.dumps({'title': '你好', 'content': '世界'})}}]}
    mock_response.raise_for_status.return_value = None
    with patch('src.translator.httpx.post', return_value=mock_response) as post:
        response = client.post('/api/translate', json={'title': 'Hello', 'content': 'World', 'target_language': '简体中文'})
    assert response.status_code == 200
    assert response.json['content'] == '世界'
    assert post.call_args.kwargs['headers']['Authorization'] == 'Bearer test-only-key'
    assert client.post('/api/translate', json={'title': '', 'content': '', 'target_language': 'English'}).status_code == 400
    assert client.post('/api/translate', json={'title': 'Hello', 'content': '', 'target_language': 'Klingon'}).status_code == 400


def test_translation_bad_response_keeps_api_safe(client, monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    mock_response = Mock()
    mock_response.json.return_value = {'choices': [{'message': {'content': 'not json'}}]}
    mock_response.raise_for_status.return_value = None
    with patch('src.translator.httpx.post', return_value=mock_response):
        response = client.post('/api/translate', json={'title': 'Hello', 'content': 'World', 'target_language': 'English'})
    assert response.status_code == 502
    assert 'test-only-key' not in response.get_data(as_text=True)

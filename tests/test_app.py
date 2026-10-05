import json
from unittest.mock import Mock, patch

import pytest
import httpx
from sqlalchemy.exc import OperationalError
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


def test_frontend_assets_and_json_errors(client):
    assert b'Translation studio' in client.get('/').data
    assert client.get('/app.js').status_code == 200
    assert client.get('/app.css').status_code == 200
    assert client.get('/api/notes/987654').json == {'error': 'Note or page not found'}
    assert client.post('/api/notes', data='x' * (1024 * 1024 + 1), content_type='application/json').status_code == 413


def test_unconfigured_translation_does_not_change_note(client, monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    note = client.post('/api/notes', json={'title': 'Original', 'content': 'Keep this text'}).json
    response = client.post('/api/translate', json={**note, 'target_language': '简体中文'})
    assert response.status_code == 503
    assert client.get(f'/api/notes/{note["id"]}').json == note


@pytest.mark.parametrize('status,expected', [(401, 502), (429, 429), (503, 502)])
def test_model_http_failures_are_safe(client, monkeypatch, status, expected):
    monkeypatch.setenv('LLM_API_KEY', 'test-only-secret')
    request = httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions')
    response = httpx.Response(status, request=request, json={'error': 'test-only-secret'})
    with patch('src.translator.httpx.post', return_value=response):
        result = client.post('/api/translate', json={'title': 'Hello', 'content': 'World', 'target_language': 'English'})
    assert result.status_code == expected
    assert 'test-only-secret' not in result.get_data(as_text=True)


def test_model_timeout(client, monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    with patch('src.translator.httpx.post', side_effect=httpx.ReadTimeout('private details')):
        result = client.post('/api/translate', json={'title': 'Hello', 'content': '', 'target_language': 'English'})
    assert result.status_code == 502
    assert 'timed out' in result.json['error']
    assert 'private details' not in result.get_data(as_text=True)


@pytest.mark.parametrize('output', [{'title': '', 'content': ''}, {'title': 'x' * 201, 'content': 'hello'}, {'title': 'Hi', 'content': 123}])
def test_translation_must_be_saveable(client, monkeypatch, output):
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    response = httpx.Response(200, request=httpx.Request('POST', 'https://example.com'),
                             json={'choices': [{'message': {'content': json.dumps(output)}}]})
    with patch('src.translator.httpx.post', return_value=response):
        result = client.post('/api/translate', json={'title': 'Hello', 'content': '', 'target_language': 'English'})
    assert result.status_code == 502


def test_database_read_and_health_failures_are_safe(client):
    error = OperationalError('private database URI', {}, Exception('private password'))
    with patch('sqlalchemy.orm.Session.execute', side_effect=error):
        for path in ('/api/notes', '/api/health'):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json == {'error': 'Database unavailable. Please try again shortly.'}


def test_database_write_failure_retains_existing_note(client):
    note = client.post('/api/notes', json={'title': 'Original', 'content': 'Keep'}).json
    with patch('src.models.user.db.session.commit', side_effect=OperationalError('secret', {}, Exception('password'))):
        result = client.put(f'/api/notes/{note["id"]}', json={'title': 'Changed', 'content': 'Changed'})
    assert result.status_code == 500
    assert 'password' not in result.get_data(as_text=True)
    assert client.get(f'/api/notes/{note["id"]}').json == note

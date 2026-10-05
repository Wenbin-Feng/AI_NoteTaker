import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import NullPool

import manage
from src.config import database_config
from src.main import create_app


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql', 'postgresql+psycopg'])
def test_supabase_normalization_and_pooling(scheme):
    result = database_config(f'{scheme}://postgres.project:encoded%40password@aws-1-region.pooler.supabase.com:6543/postgres', production=True)
    url = result['SQLALCHEMY_DATABASE_URI']
    assert url.drivername == 'postgresql+psycopg'
    assert url.password == 'encoded@password'
    assert url.query['sslmode'] == 'require'
    assert result['SQLALCHEMY_ENGINE_OPTIONS']['poolclass'] is NullPool
    assert result['SQLALCHEMY_ENGINE_OPTIONS']['connect_args']['prepare_threshold'] is None


@pytest.mark.parametrize('url', ['', 'sqlite:///:memory:', 'mysql://user:pass@localhost/db',
                                  'postgresql://postgres@localhost/db',
                                  'postgresql://postgres:pass@localhost/db?sslmode=disable'])
def test_cloud_rejects_missing_or_unsafe_database(url):
    with pytest.raises(ValueError):
        database_config(url, production=True)


def test_cloud_startup_does_not_connect_or_create_tables(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://postgres:fake@localhost:6543/postgres')
    with patch('sqlalchemy.engine.Engine.connect', side_effect=AssertionError('Unexpected connection during startup')):
        app = create_app()
    assert app.config['SQLALCHEMY_DATABASE_URI'].get_backend_name() == 'postgresql'


def test_missing_configuration_is_reported_without_secrets(monkeypatch, capsys):
    for key in manage.DEPLOY_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('LLM_API_KEY', 'not-for-output')
    assert not manage.check_config()
    output = capsys.readouterr().out
    assert 'DATABASE_URL: EMPTY' in output
    assert 'not-for-output' not in output


def test_deploy_syncs_only_runtime_values_using_stdin(monkeypatch, tmp_path, capsys):
    values = {'DATABASE_URL': 'postgresql://postgres:db-secret@localhost:6543/postgres',
              'LLM_API_KEY': 'llm-secret', 'VERCEL_TOKEN': 'deployment-secret',
              'VERCEL_ORG_ID': 'team_test', 'VERCEL_PROJECT_ID': 'prj_test',
              'LLM_BASE_URL': 'https://openrouter.ai/api/v1', 'LLM_MODEL': 'test-model'}
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(manage, 'ROOT_DIR', tmp_path)
    (tmp_path / '.env').write_text('APP_URL=\n')
    engine = MagicMock()
    completed = MagicMock(returncode=0, stdout='https://test-deploy.vercel.app\n')
    with patch('manage.create_engine', return_value=engine), patch('manage.vercel_command', return_value=['vercel']), patch('manage.subprocess.run', return_value=completed) as run:
        manage.deploy()
    calls = run.call_args_list
    assert len(calls) == 5
    assert [call.args[0][3] for call in calls[:4]] == list(manage.RUNTIME_KEYS)
    assert calls[0].kwargs['input'].startswith('postgresql+psycopg://')
    assert 'sslmode=require' in calls[0].kwargs['input']
    assert calls[1].kwargs['input'] == 'llm-secret'
    assert all('llm-secret' not in call.args[0] for call in calls)
    assert calls[-1].args[0][1:4] == ['deploy', '--prod', '--yes']
    assert json.loads((tmp_path / '.vercel' / 'project.json').read_text())['projectId'] == 'prj_test'
    assert 'https://test-deploy.vercel.app' in (tmp_path / '.env').read_text()
    assert not any(secret in capsys.readouterr().out for secret in ('llm-secret', 'db-secret', 'deployment-secret'))

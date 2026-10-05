"""Check configuration, initialize Supabase, deploy, and test a running app."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import json
from uuid import uuid4

import httpx
from dotenv import set_key
from sqlalchemy import create_engine, text

from src.config import ROOT_DIR, database_config
from src.translator import TranslationError, translate_note

RUNTIME_KEYS = ('DATABASE_URL', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL')
DEPLOY_KEYS = ('DATABASE_URL', 'LLM_API_KEY', 'VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID')


def cloud_database():
    return database_config(production=True)


def check_config(live=False):
    missing = []
    for key in DEPLOY_KEYS:
        present = bool(os.getenv(key, '').strip())
        if key == 'VERCEL_TOKEN' and not present:
            print('VERCEL_TOKEN: empty — using Vercel CLI login')
            continue
        print(f'{key}: {"configured" if present else "EMPTY — needed for deployment"}')
        if not present:
            missing.append(key)
    configured = None
    if os.getenv('DATABASE_URL', '').strip():
        configured = cloud_database()
        print('DATABASE_URL: valid Postgres URI, SSL enabled, prepared statements disabled')
    print('APP_URL: ' + ('configured' if os.getenv('APP_URL', '').strip() else 'empty — fill after deployment'))
    if live:
        if configured:
            engine = create_engine(configured['SQLALCHEMY_DATABASE_URI'], **configured['SQLALCHEMY_ENGINE_OPTIONS'])
            try:
                with engine.connect() as connection:
                    connection.execute(text('SELECT id FROM public.note LIMIT 1'))
                print('Supabase notes table: reachable')
            finally:
                engine.dispose()
        if os.getenv('LLM_API_KEY', '').strip():
            translate_note('Hello', 'This note tests the translation service.', '简体中文')
            print('Live LLM translation: passed')
    return not missing


def init_database():
    configured = cloud_database()
    engine = create_engine(configured['SQLALCHEMY_DATABASE_URI'], **configured['SQLALCHEMY_ENGINE_OPTIONS'])
    try:
        with engine.begin() as connection:
            connection.execute(text((ROOT_DIR / 'supabase' / 'schema.sql').read_text(encoding='utf-8')))
        print('Supabase note table initialized; existing notes retained.')
    finally:
        engine.dispose()


def vercel_command():
    if shutil.which('vercel'):
        return [shutil.which('vercel')]
    if shutil.which('pnpm'):
        return [shutil.which('pnpm'), 'dlx', 'vercel@62.1.0']
    if shutil.which('npx'):
        return [shutil.which('npx'), '--yes', 'vercel@62.1.0']
    raise ValueError('Install Node.js and pnpm (or Vercel CLI) before deployment')


def deploy():
    if not check_config():
        raise ValueError('Fill the EMPTY fields in .env before deploying')
    # Validate the actual table before touching the Vercel project.
    configured = cloud_database()
    engine = create_engine(configured['SQLALCHEMY_DATABASE_URI'], **configured['SQLALCHEMY_ENGINE_OPTIONS'])
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT id FROM public.note LIMIT 1'))
    finally:
        engine.dispose()
    prefix = vercel_command()
    token = os.getenv('VERCEL_TOKEN', '').strip()
    organization = os.environ['VERCEL_ORG_ID'].strip()
    project = os.environ['VERCEL_PROJECT_ID'].strip()
    link = ROOT_DIR / '.vercel' / 'project.json'
    if link.exists():
        current = json.loads(link.read_text(encoding='utf-8'))
        if current.get('orgId') != organization or current.get('projectId') != project:
            raise ValueError('Existing .vercel project differs from .env; check the target project first')
    else:
        link.parent.mkdir(exist_ok=True)
        link.write_text(json.dumps({'orgId': organization, 'projectId': project}), encoding='utf-8')

    def run(arguments, value=None):
        # Values go through stdin, never through an echoed shell command.
        authentication = ['--token', token] if token else []
        result = subprocess.run(prefix + arguments + authentication,
                                cwd=ROOT_DIR, input=value, text=True,
                                capture_output=True, timeout=600)
        if result.returncode:
            # CLI diagnostics can contain configuration; keep credentials out of output.
            raise ValueError(f'Vercel {arguments[0]} failed (exit {result.returncode}); check project access and CLI authentication')
        return result.stdout

    for key in RUNTIME_KEYS:
        value = os.environ.get(key, '').strip()
        if key == 'DATABASE_URL':
            value = configured['SQLALCHEMY_DATABASE_URI'].render_as_string(hide_password=False)
        elif key == 'LLM_BASE_URL':
            value = value or 'https://openrouter.ai/api/v1'
        elif key == 'LLM_MODEL':
            value = value or 'nvidia/nemotron-3-ultra-550b-a55b:free'
        run(['env', 'add', key, 'production', '--force', '--yes'], value)
        print(f'Vercel production environment updated: {key}')
    print('Building and deploying the production app…')
    output = run(['deploy', '--prod', '--yes'])
    urls = re.findall(r'https://[a-zA-Z0-9.-]+\.vercel\.app', output)
    if not urls:
        raise ValueError('Deployment completed but no URL was returned; copy the production URL from Vercel')
    url = urls[-1]
    set_key(ROOT_DIR / '.env', 'APP_URL', url)
    os.environ['APP_URL'] = url
    print(f'Production deployment: {url}')
    print('Make the submitted URL public in Vercel Deployment Protection, then run manage.py smoke --translate.')


def smoke(base_url, translation=False):
    if not base_url:
        raise ValueError('Fill APP_URL or pass --url http://127.0.0.1:5001')
    if not base_url.startswith(('https://', 'http://')):
        raise ValueError('APP_URL must start with https:// or http://')
    note_ids = []
    with httpx.Client(base_url=base_url.rstrip('/') + '/', timeout=90, follow_redirects=True) as client:
        def request(method, path, expected=200, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.status_code != expected:
                raise ValueError(f'{method} {path}: expected {expected}, received {response.status_code}')
            if expected != 204 and path.startswith('api/') and 'application/json' not in response.headers.get('content-type', ''):
                raise ValueError('The URL returned a login/HTML page; check Deployment Protection')
            return response
        try:
            request('GET', '')
            for asset in ('app.js', 'app.css'):
                request('GET', asset)
            request('GET', 'api/health')
            print('Public UI, static assets, and database health: passed')
            request('POST', 'api/notes', expected=400, json={'title': '', 'content': ''})
            label = f'Deployment test {uuid4().hex[:12]}'
            body = {'title': label, 'content': 'Software engineering improves how teams build and maintain software.'}
            created = request('POST', 'api/notes', expected=201, json=body).json()
            note_ids.append(created['id'])
            path = f'api/notes/{created["id"]}'
            assert request('GET', path).json()['content'] == body['content']
            found = request('GET', 'api/notes', params={'q': label}).json()
            assert any(note['id'] == created['id'] for note in found)
            updated = {**body, 'content': body['content'] + '\nA second paragraph.'}
            assert request('PUT', path, json=updated).json()['content'] == updated['content']
            print('Create, read, search, update, and invalid-input checks: passed')
            if translation:
                result = request('POST', 'api/translate', json={**updated, 'target_language': '简体中文'}).json()
                assert isinstance(result['title'], str) and isinstance(result['content'], str)
                translated = request('POST', 'api/notes', expected=201,
                                     json={key: result[key] for key in ('title', 'content')}).json()
                note_ids.append(translated['id'])
                assert request('GET', path).json()['content'] == updated['content']
                print('Live translation, save-as-new, and original-note preservation: passed')
            request('POST', 'api/translate', expected=400,
                    json={'title': 'Hello', 'content': 'World', 'target_language': 'Klingon'})
            for note_id in list(note_ids):
                request('DELETE', f'api/notes/{note_id}', expected=204)
                note_ids.remove(note_id)
                request('GET', f'api/notes/{note_id}', expected=404)
            print('Delete and missing-note checks: passed; test notes removed')
        finally:
            for note_id in note_ids:
                try:
                    response = client.delete(f'api/notes/{note_id}')
                    if response.status_code not in (204, 404):
                        print(f'Cleanup needed: delete test note {note_id}', file=sys.stderr)
                except httpx.HTTPError:
                    print(f'Cleanup needed: delete test note {note_id}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check-config', help='List missing values without exposing secrets')
    check.add_argument('--live', action='store_true', help='Test configured Supabase and LLM connections')
    commands.add_parser('init-db', help='Create the Supabase table and disable direct Data API access')
    commands.add_parser('deploy', help='Sync production runtime variables and deploy through Vercel CLI')
    test = commands.add_parser('smoke', help='Test the running app using disposable test notes')
    test.add_argument('--url', default=os.getenv('APP_URL', '').strip())
    test.add_argument('--translate', action='store_true', help='Also call the live LLM and save its result')
    args = parser.parse_args()
    try:
        if args.command == 'check-config':
            return 0 if check_config(args.live) else 1
        if args.command == 'init-db':
            init_database()
        elif args.command == 'deploy':
            deploy()
        elif args.command == 'smoke':
            smoke(args.url, args.translate)
        return 0
    except (ValueError, TranslationError) as error:
        print(f'Action needed: {error}', file=sys.stderr)
        return 1
    except Exception as error:
        print(f'Action failed ({type(error).__name__}). Check database/network access; credentials were not printed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

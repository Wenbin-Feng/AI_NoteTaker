"""Shared local/cloud configuration, without logging credentials."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')


def database_config(database_url=None, *, production=None):
    production = bool(os.getenv('VERCEL')) if production is None else production
    raw = (os.getenv('DATABASE_URL', '') if database_url is None else database_url).strip()
    if not raw:
        if production:
            raise ValueError('Fill DATABASE_URL with the Supabase Postgres connection URI')
        path = ROOT_DIR / 'database' / 'app.db'
        path.parent.mkdir(exist_ok=True)
        raw = f'sqlite:///{path}'
    try:
        url = make_url(raw)
        backend = url.get_backend_name()
        if backend == 'postgres':
            backend = 'postgresql'
        if backend == 'sqlite':
            if production:
                raise ValueError('Vercel requires Supabase Postgres; SQLite is local only')
            return {'SQLALCHEMY_DATABASE_URI': str(url),
                    'SQLALCHEMY_ENGINE_OPTIONS': {'pool_pre_ping': True}}
        if backend != 'postgresql' or not url.host or not url.username or not url.password or not url.database:
            raise ValueError('Use a complete Supabase Postgres connection URI')
        url = url.set(drivername='postgresql+psycopg')
        sslmode = url.query.get('sslmode', 'require')
        if sslmode not in {'require', 'verify-ca', 'verify-full'}:
            raise ValueError('DATABASE_URL must use sslmode=require or certificate verification')
        url = url.update_query_dict({'sslmode': sslmode})
        return {'SQLALCHEMY_DATABASE_URI': url,
                'SQLALCHEMY_ENGINE_OPTIONS': {
                    'poolclass': NullPool,
                    'connect_args': {'connect_timeout': 10, 'prepare_threshold': None},
                }}
    except ValueError:
        raise
    except Exception:
        raise ValueError('DATABASE_URL is not a valid Postgres connection URI') from None

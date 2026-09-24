"""Flask application entry point for local development and Vercel."""
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from src.models.user import db
from src.models.note import Note  # noqa: F401 - registers the model
from src.routes.note import note_bp

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

def create_app(test_config=None):
    app = Flask(__name__, static_folder=str(ROOT_DIR / 'src' / 'static'))
    database_url = os.getenv('DATABASE_URL', '').strip()
    if database_url.startswith('postgres://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgres://'):]
    elif database_url.startswith('postgresql://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgresql://'):]
    if not database_url:
        if os.getenv('VERCEL'):
            raise RuntimeError('DATABASE_URL must be configured for Vercel deployment')
        database_path = ROOT_DIR / 'database' / 'app.db'
        database_path.parent.mkdir(exist_ok=True)
        database_url = f'sqlite:///{database_path}'
    app.config.update(SQLALCHEMY_DATABASE_URI=database_url,
                      SQLALCHEMY_TRACK_MODIFICATIONS=False,
                      SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True},
                      MAX_CONTENT_LENGTH=1024 * 1024)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    app.register_blueprint(note_bp, url_prefix='/api')
    with app.app_context():
        db.create_all()

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    @app.get('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/<path:path>')
    def serve_asset(path):
        return send_from_directory(app.static_folder, path)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5001')), debug=os.getenv('FLASK_DEBUG') == '1')

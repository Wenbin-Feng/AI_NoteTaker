"""Flask application entry point for local development and Vercel."""
import os
from flask import Flask, send_from_directory
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from src.config import ROOT_DIR, database_config
from src.models.user import db
from src.models.note import Note  # noqa: F401 - registers the model
from src.routes.note import note_bp

def create_app(test_config=None):
    app = Flask(__name__, static_folder=str(ROOT_DIR / 'public'))
    override_url = (test_config or {}).get('SQLALCHEMY_DATABASE_URI')
    app.config.update(database_config(override_url))
    app.config.update(
                      SQLALCHEMY_TRACK_MODIFICATIONS=False,
                      MAX_CONTENT_LENGTH=1024 * 1024)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    app.register_blueprint(note_bp, url_prefix='/api')
    with app.app_context():
        if db.engine.dialect.name == 'sqlite':
            Note.__table__.create(db.engine, checkfirst=True)

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        return {'error': 'Database unavailable. Please try again shortly.'}, 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        if error.code == 404:
            message = 'Note or page not found'
        elif error.code == 413:
            message = 'Request is too large'
        else:
            message = error.name
        return {'error': message}, error.code

    @app.get('/api/health')
    def health():
        db.session.execute(select(Note.id).limit(1)).first()
        return {'status': 'ok'}

    @app.get('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/<path:path>')
    def serve_asset(path):
        return send_from_directory(app.static_folder, path)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5001')), debug=os.getenv('FLASK_DEBUG') == '1')

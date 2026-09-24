"""Notes and translation API."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from src.models.note import Note, db
from src.translator import TranslationError, translate_note

note_bp = Blueprint('note', __name__)

def validate_note(data):
    if not isinstance(data, dict):
        return None, 'Expected a JSON object'
    title, content = data.get('title'), data.get('content')
    if not isinstance(title, str) or not isinstance(content, str):
        return None, 'Title and content must be text'
    title, content = title.strip(), content.strip()
    if not title and not content:
        return None, 'Enter a title or content'
    if len(title) > 200 or len(content) > 50000:
        return None, 'Title or content is too long'
    return {'title': title or 'Untitled', 'content': content}, None

@note_bp.get('/notes')
def get_notes():
    q = request.args.get('q', '').strip()
    query = Note.query
    if q:
        query = query.filter(or_(Note.title.ilike(f'%{q}%'), Note.content.ilike(f'%{q}%')))
    notes = query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.get('/notes/search')
def search_notes():
    return get_notes()

@note_bp.post('/notes')
def create_note():
    data, error = validate_note(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    note = Note(**data)
    try:
        db.session.add(note)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Could not save the note'}), 500
    return jsonify(note.to_dict()), 201

@note_bp.get('/notes/<int:note_id>')
def get_note(note_id):
    return jsonify(db.get_or_404(Note, note_id).to_dict())

@note_bp.put('/notes/<int:note_id>')
def update_note(note_id):
    note = db.get_or_404(Note, note_id)
    data, error = validate_note(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    note.title, note.content = data['title'], data['content']
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Could not update the note'}), 500
    return jsonify(note.to_dict())

@note_bp.delete('/notes/<int:note_id>')
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    try:
        db.session.delete(note)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Could not delete the note'}), 500
    return '', 204

@note_bp.post('/translate')
def translate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Expected a JSON object'}), 400
    title, content, language = data.get('title', ''), data.get('content', ''), data.get('target_language', '')
    if not all(isinstance(v, str) for v in (title, content, language)):
        return jsonify({'error': 'Translation fields must be text'}), 400
    if not (title.strip() or content.strip()):
        return jsonify({'error': 'Write something before translating'}), 400
    if len(title) > 200 or len(content) > 50000 or len(language) > 50:
        return jsonify({'error': 'Translation input is too long'}), 400
    try:
        return jsonify(translate_note(title, content, language))
    except TranslationError as exc:
        return jsonify({'error': str(exc)}), exc.status_code

"""Server-side OpenRouter translation. Credentials never reach the browser."""
import json
import os
from pathlib import Path
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPT = (ROOT_DIR / 'prompts' / 'translate_prompt.md').read_text(encoding='utf-8')

class TranslationError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code

def translate_note(title, content, target_language):
    language = target_language.strip()
    if language not in {'English', '简体中文', '繁體中文', '日本語', '한국어', 'Français', 'Español', 'Deutsch'}:
        raise TranslationError('Choose a supported target language', 400)
    key = os.getenv('LLM_API_KEY', '').strip()
    if not key:
        raise TranslationError('Translation is not configured on this server', 503)
    base_url = (os.getenv('LLM_BASE_URL', '').strip() or 'https://openrouter.ai/api/v1').rstrip('/')
    model = os.getenv('LLM_MODEL', '').strip() or 'nvidia/nemotron-3-ultra-550b-a55b:free'
    payload = {'model': model, 'temperature': 0.2,
               'messages': [
                   {'role': 'system', 'content': PROMPT.replace('{target_language}', language)},
                   {'role': 'user', 'content': json.dumps({'title': title, 'content': content}, ensure_ascii=False)}]}
    try:
        response = httpx.post(f'{base_url}/chat/completions',
                              headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                              json=payload, timeout=httpx.Timeout(50, connect=10))
        response.raise_for_status()
        raw = response.json()['choices'][0]['message']['content']
        if not isinstance(raw, str):
            raise ValueError('Empty translation response')
        raw = raw.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        result = json.loads(raw)
        if not isinstance(result, dict) or not all(isinstance(result.get(k), str) for k in ('title', 'content')):
            raise ValueError('Invalid translation JSON')
        if len(result['title']) > 200 or len(result['content']) > 50000 or not (result['title'].strip() or result['content'].strip()):
            raise ValueError('Translation cannot be saved as a note')
        return {'title': result['title'], 'content': result['content'], 'target_language': language}
    except httpx.TimeoutException as exc:
        raise TranslationError('Translation timed out. Please try again.') from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise TranslationError('The translation service is busy. Please try again shortly.', 429) from exc
        raise TranslationError('Translation service is unavailable. Please try again.') from exc
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise TranslationError('Could not read the translation. Please try again.') from exc

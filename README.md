# Margin — AI note studio

A polished note-taking app based on [HKPolyUSE/MyNoteTaking](https://github.com/HKPolyUSE/MyNoteTaking). Notes support create, edit, delete, search and auto-save. The translation studio uses OpenRouter on the server, returns structured JSON, and lets you copy or save a translation as a new note.

## Run locally with uv

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
cp .env.example .env
# Add your OpenRouter API key to .env
uv sync
uv run python -m src.main
```

Open <http://127.0.0.1:5001>. Leaving `DATABASE_URL` unset uses local SQLite at `database/app.db`. The local `.env`, `.venv` and database files are gitignored. To use another port, set `PORT` in your shell or `.env`.

## Translate from the command line

```sh
uv run python translator.py "Hello, world" --to 简体中文
```

See [tutorial.md](tutorial.md) and [prompts/translate_prompt.md](prompts/translate_prompt.md).

## Switch to Supabase later

Create a Supabase Postgres project and copy its **Session Pooler** URI into `DATABASE_URL` in `.env`. Use a URL beginning `postgresql+psycopg://` and include `sslmode=require`. The server creates the notes table when it starts. Your local SQLite notes are **not** copied automatically; export/import them if you need to keep them. Keep this connection string server-side and out of Git.

## Vercel deployment preparation

`api/index.py` and `vercel.json` contain the Python Function entry point and routing. Set `DATABASE_URL`, `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` as Vercel project environment variables before deploying. Vercel requires Postgres because its local file system is ephemeral. A live public deployment cannot be verified until a Supabase project and Vercel project are supplied. For a public class demo, be aware that notes in this starter app are shared; it has no accounts or access control.

## Test

```sh
uv run pytest -q
```

The tests cover note CRUD, validation, translation success and failures using a mocked model response. The real OpenRouter endpoint may be temporarily busy or reject free-model traffic; the UI reports that error without losing the note.

## API

- `GET /api/notes` and `GET /api/notes?q=term`
- `POST /api/notes`
- `GET`, `PUT`, `DELETE /api/notes/<id>`
- `POST /api/translate` with `title`, `content`, `target_language`
- `GET /api/health`

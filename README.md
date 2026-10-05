# Margin — AI note studio

A polished note-taking app based on [HKPolyUSE/MyNoteTaking](https://github.com/HKPolyUSE/MyNoteTaking). Notes support create, edit, delete, search and auto-save. The translation studio uses OpenRouter on the server, returns structured JSON, and lets you copy or save a translation as a new note.

Project repository: [Wenbin-Feng/AI_NoteTaker](https://github.com/Wenbin-Feng/AI_NoteTaker).

Public application: [Margin AI NoteTaker](https://ai-notetaker-three.vercel.app).

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

## Supabase and Vercel

Fill the empty fields in `.env` using [DEPLOYMENT.md](DEPLOYMENT.md). This app connects directly to Supabase Postgres, so a Supabase anon key or service-role key is not required. The database connection automatically uses SSL and disables prepared statements for transaction pooling.

```sh
uv run python manage.py check-config
uv run python manage.py init-db
uv run python manage.py check-config --live
uv run python manage.py deploy
uv run python manage.py smoke --translate
```

`init-db` applies the repeatable SQL in `supabase/schema.sql`. Cloud startup does not create tables or write SQLite files. Local SQLite notes are retained locally and are not copied to Supabase automatically.

`app.py` is the Flask entrypoint. Vercel serves the `public/` assets and routes API requests to the Python Function. The deploy command sends the four app runtime variables to Vercel Production through stdin, invokes Vercel CLI, and saves the resulting URL to `APP_URL`. Deployment tokens and IDs are only used by the local deployment tool. Notes in this class demo are shared; the app has no user accounts.

## Test

```sh
uv run pytest -q
```

The tests cover note CRUD, validation, translation success and failures, database failures, cloud configuration, and the deployment command using mocked external services. `manage.py smoke` tests a running local or deployed instance, creates temporary test notes, then removes them. See [TESTING.md](TESTING.md) for the latest verification record.

## API

- `GET /api/notes` and `GET /api/notes?q=term`
- `POST /api/notes`
- `GET`, `PUT`, `DELETE /api/notes/<id>`
- `POST /api/translate` with `title`, `content`, `target_language`
- `GET /api/health`

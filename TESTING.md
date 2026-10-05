# Test record

## Public Vercel deployment (2026-10-05)

- Public URL: https://ai-notetaker-three.vercel.app
- Deployment created through Vercel CLI 62.1.0 with the Flask framework preset. Vercel Authentication was disabled on this project for public course access.
- `uv run python manage.py smoke --translate`: **passed against the public URL with real Supabase and real OpenRouter**. UI/assets, database health, note CRUD/search, input validation, translation, save-as-new, original preservation, and deletion passed. Temporary test notes were removed.
- Browser verification: autosaved a note on the public app and received a real Chinese translation. The observed model double-escaped paragraph breaks; the translator now repairs this when the source contains real newlines and no literal backslash-n sequences.
- `uv run pytest -q`: **28 passed**, including CLI-login deployment authentication and paragraph-break regression cases.
- Browser assets contain no configured credentials; requests for `.env`, `.env.local`, `.vercel/project.json`, and server source return 404.
- Final Task 1 PDF contains the public URL and production screenshot, with two pages visually reviewed.
- Earlier pending-deployment statements below are historical test records.

## Supabase connection attempt (2026-10-05)

The supplied direct Postgres URI initially failed because it resolves to an IPv6 address only and this machine reported `No route to host`. The user then supplied the Transaction pooler template. The ignored `.env` now uses the pooler on port 6543, the previously supplied password, and `sslmode=require`.

- `uv run python manage.py init-db`: **passed against real Supabase**; initialized `public.note` with RLS and retained existing data.
- `uv run python manage.py smoke --url http://127.0.0.1:5011 --translate`: **passed with real Supabase and real OpenRouter**. UI/assets, database health, note CRUD/search, invalid input, translation, save-as-new, original preservation, and missing-note responses passed. Temporary test notes were removed.
- Still pending: Vercel deployment and production screenshots. `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` remain empty; `APP_URL` will be recorded after deployment.

No credentials are recorded in this test log.

## Latest verification (2026-10-02)

- `uv run pytest -q`: **25 passed**. Includes missing LLM key, timeout, upstream 401/429/503, invalid or unsaveable model output, database read/write failures, JSON 404/413 responses, production SQLite rejection, Postgres SSL/pooling configuration, cloud startup without database I/O, and mocked Vercel environment synchronization/deployment.
- `uv run python manage.py smoke --url http://127.0.0.1:5011 --translate`: **passed using the actual configured OpenRouter model**. UI/static assets, database health, CRUD/search, invalid input, live translation, save-as-new and original preservation were checked. Temporary smoke-test notes were removed.
- Browser UI: created and autosaved an English note, translated it to Simplified Chinese through the live API, and saved the translation as a new note while retaining the original. No browser console errors. Screenshot: `submission/screenshots/local-translation.png`.
- `vercel.json` properties validated against the official Vercel JSON schema. Vercel CLI **62.1.0** is available through `pnpm dlx`.
- **Not verified:** real Supabase database access, Vercel build/deployment, publicly accessible production URL. `DATABASE_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` are still empty. CLI deployment inspection required login and was stopped; no deployment was created.

After filling the credentials, run the sequence in `DEPLOYMENT.md`, then replace local evidence with production evidence.

## Automated checks

Run `uv run pytest -q`. The suite covers empty-note validation, create/read/update/delete, search, missing note, a valid translation response, rejected target language, missing text, malformed model output, and key-free API errors. Model responses are mocked in the suite so these checks are repeatable.

## Manual browser checks (2026-09-24)

| Case | Expected | Result |
| --- | --- | --- |
| New note and type in title/content | Autosave creates one note and updates the list | Passed |
| Open translation studio | Result is shown separately from original note | Passed using the configured OpenRouter model |
| Save translation as new | New note is added, original retained | Passed |
| Narrow mobile viewport | No horizontal overflow; panels stack vertically | Visually checked |

The provided free model may be temporarily rate limited. In that case, the app shows a retryable error and retains the note. Supabase and Vercel integration remain unverified until project credentials are supplied.

## Issues found in the starter app and addressed

- The delete button appeared for an unsaved note; it now appears only after the note has an ID.
- The original note API returned raw exception text; write failures now return safe, actionable messages.
- Search and note editing now use semantic controls and text nodes, so note content is not inserted as HTML.

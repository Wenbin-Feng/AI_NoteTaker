# Test record

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

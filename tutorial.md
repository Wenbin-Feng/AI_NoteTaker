# How the translator works

`translator.py` accepts text and an optional target language from the command line. It loads `.env` locally, then calls the same `translate_note()` function used by the web app.

`src/translator.py` reads `prompts/translate_prompt.md`, inserts the target language, and sends the note as JSON to OpenRouter's chat completion endpoint. The system instruction asks for a JSON object containing `title` and `content`. The response is checked before it is returned. Network, timeout, rate limit, and malformed response errors become safe messages; the API key is never sent to the browser.

Run it with:

```sh
uv run python translator.py "How are you?" --to 简体中文
```

The web UI posts to `/api/translate`; the Flask server runs this function. Translation only changes the original note if you explicitly copy text into it. The **Save as new** action stores a separate note.

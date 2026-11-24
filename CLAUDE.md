# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Telegram bot that transcribes voice and audio messages to text and can translate them. The whole app is `bot.py`: python-telegram-bot (v22, async) handles Telegram, and AssemblyAI does both transcription (with automatic language detection) and translation. Bot UI strings live in `i18n.py`.

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python bot.py          # runs the bot with long polling
```

Tests (pytest + pytest-asyncio, `asyncio_mode = auto` in `pytest.ini`):

```bash
pip install -r requirements-dev.txt
pytest                                                  # all tests
pytest tests/test_handlers.py::test_voice_empty_text    # single test
```

Tests never hit the network. Handlers get `SimpleNamespace`/`AsyncMock` fakes for Telegram objects (helpers in `tests/conftest.py`), and `bot.transcribe` / `bot.translate_existing` / `aai.Transcriber` / `aai.LLMGateway` are monkeypatched. There is no linter.

## CI/CD and deployment

`.github/workflows/ci-cd.yml` runs `test` on pushes to `main` and on PRs. On `main` (push or manual run) it then runs `build`, which pushes `ghcr.io/idachser/speech_recognition:latest` and `:<sha>` to GHCR, and then `deploy`. `deploy` copies `compose.yaml` to `~/www/speech_recognition` on the VPS (`DEPLOY_DIR` in the workflow, the same directory that holds the old systemd checkout and its dotenv file) over SSH and runs `docker compose pull && up -d`, logging into GHCR with the job's short-lived `GITHUB_TOKEN`. The SSH settings come from repository secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS` and optional `VPS_PORT`, used in the `production` environment.

- The image copies only `bot.py` and `requirements.txt` (`.dockerignore` whitelist). A new runtime file must be added to both `Dockerfile` and `.dockerignore`.
- The container's working directory is the `/data` volume, so `bot_data.pickle` and `enotebot.log` (both written relative to cwd) survive redeploys.
- The server's `.env` sits next to `compose.yaml` and reaches the container through `env_file`. It is never in the image or the repo.
- Only one instance may poll a bot token at a time. Two running copies (for example the old systemd service plus the container) cause Telegram `Conflict` errors.

Configuration comes from a `.env` file (gitignored) loaded by `python-dotenv`. It needs `TELEGRAM_API_TOKEN` and `ASSEMBLYAI_API_KEY`.

## How it works

- Logs go to `enotebot.log` (not stdout), and the file is truncated on every start (`filemode="w"`). Logging is configured only in the `__main__` block, so importing `bot` (as the tests do) doesn't touch the log file.
- User settings (`context.user_data["translate"]`) persist across restarts in `bot_data.pickle` via `PicklePersistence`.
- `telegram_token` is a module-level global assigned in the `if __name__ == "__main__":` block and read by `main()`. Calling `main()` from anywhere else (an import, a test) fails unless that global is set first.
- The voice handler only fires in private chats (`filters.ChatType.PRIVATE`) for `VOICE` or `AUDIO` messages.
- The handler does not download the audio. It passes Telegram's file URL (`get_file(...).file_path`) straight to AssemblyAI, which fetches it.
- The AssemblyAI SDK is synchronous, so its calls run in `asyncio.to_thread`, and the voice and translate handlers are registered with `block=False` so several messages can be processed at once.
- The translation target is the user's Telegram `language_code` (base part only, `en` if missing). Translation is offered only when the detected speech language differs from it.
- There are two translation paths. With `/settings` on, translation is requested in the same transcription call (`speech_understanding` → `TranslationRequest`, result in `transcript.translated_texts`). With it off, or if that translation came back empty, a foreign-language reply gets a "Перевести" button whose `callback_data` is `tr:<transcript_id>`. Pressing it calls `aai.LLMGateway().understanding.create(...)` on the existing transcript and edits the message.
- UI language follows the user's Telegram `language_code`. `i18n.TEXTS` has `ru`, `en`, `uk`, `de`, `es`, `fr`, `it`, `pt`, `pl`, `tr`, `ar` and `zh`, with `en` (`DEFAULT_LANGUAGE`) for any other language and when the code is missing. Every language must have the same keys, which `tests/test_i18n.py` checks. In `bot.py`, `tr(user, key, ...)` is the lookup helper. To add a language, add a `TEXTS` entry; the localized command menu is registered from `TEXTS` in `post_init` (`set_commands`).
- `set_commands` swallows `TelegramError` on purpose: `post_init` runs outside the bootstrap retry loop, so an exception there would crash the bot into a container restart loop.
- Telegram's 4096-character limit is handled by splitting long texts (`chunks` / `reply_long`).

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Telegram bot that transcribes voice and audio messages to text and can translate them. The whole app is `bot.py`: python-telegram-bot (v22, async) handles Telegram, and AssemblyAI does both transcription (with automatic language detection) and translation. User-facing strings are in Russian.

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

Tests never hit the network. Handlers get `SimpleNamespace`/`AsyncMock` fakes for Telegram objects (helpers in `tests/conftest.py`), and `bot.transcribe` / `bot.translate_existing` / `aai.Transcriber` / `aai.LLMGateway` are monkeypatched. There is no linter or build step.

Configuration comes from a `.env` file (gitignored) loaded by `python-dotenv`. It needs `TELEGRAM_API_TOKEN` and `ASSEMBLYAI_API_KEY`.

## How it works

- Logs go to `enotebot.log` (not stdout), and the file is truncated on every start (`filemode="w"`). Logging is configured only in the `__main__` block, so importing `bot` (as the tests do) doesn't touch the log file.
- User settings (`context.user_data["translate"]`) persist across restarts in `bot_data.pickle` via `PicklePersistence`.
- `telegram_token` is a module-level global assigned in the `if __name__ == "__main__":` block and read by `main()`. Calling `main()` from anywhere else (an import, a test) fails unless that global is set first.
- The voice handler only fires in private chats (`filters.ChatType.PRIVATE`) for `VOICE` or `AUDIO` messages.
- The handler does not download the audio. It passes Telegram's file URL (`get_file(...).file_path`) straight to AssemblyAI, which fetches it.
- The AssemblyAI SDK is synchronous, so its calls run in `asyncio.to_thread`, and the voice and translate handlers are registered with `block=False` so several messages can be processed at once.
- The translation target is the user's Telegram `language_code` (base part only, `ru` if missing). Translation is offered only when the detected speech language differs from it.
- There are two translation paths. With `/settings` on, translation is requested in the same transcription call (`speech_understanding` → `TranslationRequest`, result in `transcript.translated_texts`). With it off, or if that translation came back empty, a foreign-language reply gets a "Перевести" button whose `callback_data` is `tr:<transcript_id>`. Pressing it calls `aai.LLMGateway().understanding.create(...)` on the existing transcript and edits the message.
- Telegram's 4096-character limit is handled by splitting long texts (`chunks` / `reply_long`).

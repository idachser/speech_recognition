Telegram Bot for voice messages to text recognition

- Recognizes voice and audio messages in any language (AssemblyAI language detection).
- Translates transcripts into the language of the user's Telegram interface: always (toggle in `/settings`) or on demand with the "Перевести" button under a transcript.

Setup: `pip install -r requirements.txt`, set `TELEGRAM_API_TOKEN` and `ASSEMBLYAI_API_KEY` in the dotenv file, run `python bot.py`. User settings are stored in `bot_data.pickle`.

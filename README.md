Telegram Bot for voice messages to text recognition

- Recognizes voice and audio messages in any language (AssemblyAI language detection).
- Translates transcripts automatically or on demand with the "Перевести" button under a transcript. The "⚙️ Настройки" button under the input field (or `/settings`) opens the menu: translate into the Telegram interface language, into another language (just write its name, e.g. "немецкий", "Deutsch" or "de"), or don't translate.

Local setup: `pip install -r requirements.txt`, set `TELEGRAM_API_TOKEN` and `ASSEMBLYAI_API_KEY` in the dotenv file, run `python bot.py`. User settings are stored in `bot_data.pickle`. Tests: `pip install -r requirements-dev.txt && pytest`.

## Deployment

Every push to `main` runs the tests, builds a Docker image, pushes it to `ghcr.io/idachser/speech_recognition` and restarts the bot on the VPS with Docker Compose. The workflow can also be started by hand from the Actions tab.

### One-time server setup

1. Install Docker with the Compose plugin and make sure the deploy user can run `docker`.
2. Create `~/www/speech_recognition/` and put the dotenv file with `TELEGRAM_API_TOKEN` and `ASSEMBLYAI_API_KEY` in it. The workflow uploads `compose.yaml` there on every deploy.
3. Add the deploy public key to `~/.ssh/authorized_keys` of the deploy user.

### GitHub secrets

In the repository settings, create the environment `production` and add these secrets:

| Secret | Value |
| --- | --- |
| `VPS_HOST` | server address |
| `VPS_USER` | deploy user |
| `VPS_SSH_KEY` | private key of the deploy key pair |
| `VPS_KNOWN_HOSTS` | output of `ssh-keyscan <host>` |
| `VPS_PORT` | SSH port, optional (default 22) |

### Moving from the systemd service

Stop the old service before the first deploy (`sudo systemctl disable --now <service>`). Telegram allows only one process to poll a bot token, so the old service and the container cannot run at the same time.

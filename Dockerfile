FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY bot.py i18n.py ./

# bot.py writes bot_data.pickle and enotebot.log to the working directory,
# so running from /data keeps them on the mounted volume.
RUN useradd --create-home --uid 1000 bot \
    && mkdir /data && chown bot:bot /data
USER bot
WORKDIR /data
VOLUME /data

CMD ["python", "/app/bot.py"]

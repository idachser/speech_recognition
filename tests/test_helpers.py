from types import SimpleNamespace
from unittest.mock import MagicMock

import assemblyai as aai
import pytest

import bot
from conftest import make_message, make_user


@pytest.mark.parametrize(
    "code, expected",
    [("en", "en"), ("en_us", "en"), ("pt-BR", "pt"), ("UK", "uk"), (None, "ru"), ("", "ru")],
)
def test_base_language(code, expected):
    assert bot.base_language(code) == expected


def test_target_language_uses_telegram_language():
    assert bot.target_language(make_user("de")) == "de"
    assert bot.target_language(make_user(None)) == "ru"


def test_translate_enabled_defaults_to_false():
    assert bot.translate_enabled(SimpleNamespace(user_data={})) is False
    assert bot.translate_enabled(SimpleNamespace(user_data={"translate": True})) is True


def test_with_translation_format():
    assert bot.with_translation("hi", "привет", "ru") == "hi\n\n🌐 Перевод (ru):\nпривет"


def test_chunks_respects_telegram_limit():
    parts = bot.chunks("a" * (bot.MAX_LEN * 2 + 1))
    assert [len(p) for p in parts] == [bot.MAX_LEN, bot.MAX_LEN, 1]
    assert bot.chunks("short") == ["short"]


async def test_reply_long_puts_markup_on_last_part_only():
    message = make_message()
    markup = object()
    await bot.reply_long(message, "a" * (bot.MAX_LEN + 5), reply_markup=markup)

    calls = message.reply_text.await_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["reply_markup"] is None
    assert calls[1].kwargs["reply_markup"] is markup


def test_settings_keyboard_marks_current_choice():
    on, off = bot.settings_keyboard(True).inline_keyboard[0]
    assert (on.text, off.text) == ("✅ Переводить", "Не переводить")
    assert (on.callback_data, off.callback_data) == ("settings:on", "settings:off")

    on, off = bot.settings_keyboard(False).inline_keyboard[0]
    assert (on.text, off.text) == ("Переводить", "✅ Не переводить")


class FakeTranscriber:
    instances = []

    def __init__(self, config):
        self.config = config
        self.result = SimpleNamespace(status=aai.TranscriptStatus.completed, error=None)
        FakeTranscriber.instances.append(self)

    def transcribe(self, url):
        self.url = url
        return self.result


@pytest.fixture
def fake_transcriber(monkeypatch):
    FakeTranscriber.instances = []
    monkeypatch.setattr(bot.aai, "Transcriber", FakeTranscriber)
    return FakeTranscriber


def test_transcribe_without_translation(fake_transcriber):
    bot.transcribe("https://file", None)

    transcriber = fake_transcriber.instances[0]
    assert transcriber.url == "https://file"
    assert transcriber.config.language_detection is True
    assert transcriber.config.language_code is None
    assert transcriber.config.speech_understanding is None


def test_transcribe_requests_translation(fake_transcriber):
    bot.transcribe("https://file", "ru")

    understanding = fake_transcriber.instances[0].config.speech_understanding
    assert understanding.request.translation.target_languages == ["ru"]


def test_transcribe_raises_on_error_status(monkeypatch):
    class Failing(FakeTranscriber):
        def transcribe(self, url):
            return SimpleNamespace(status=aai.TranscriptStatus.error, error="bad audio")

    monkeypatch.setattr(bot.aai, "Transcriber", Failing)
    with pytest.raises(RuntimeError, match="bad audio"):
        bot.transcribe("https://file", None)


def test_translate_existing(monkeypatch):
    gateway = MagicMock()
    gateway.understanding.create.return_value = SimpleNamespace(
        translated_texts={"ru": "привет"}
    )
    monkeypatch.setattr(bot.aai, "LLMGateway", lambda: gateway)

    assert bot.translate_existing("t-1", "ru") == "привет"
    gateway.understanding.create.assert_called_once_with(
        transcript_id="t-1",
        request={"translation": {"target_languages": ["ru"]}},
    )


@pytest.mark.parametrize("texts", [None, {}, {"de": "hallo"}])
def test_translate_existing_missing_language(monkeypatch, texts):
    gateway = MagicMock()
    gateway.understanding.create.return_value = SimpleNamespace(translated_texts=texts)
    monkeypatch.setattr(bot.aai, "LLMGateway", lambda: gateway)

    assert bot.translate_existing("t-1", "ru") is None

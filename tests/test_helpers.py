from types import SimpleNamespace
from unittest.mock import MagicMock

import assemblyai as aai
import pytest

import bot
from conftest import make_message, make_user


@pytest.mark.parametrize(
    "code, expected",
    [("en", "en"), ("en_us", "en"), ("pt-BR", "pt"), ("UK", "uk"), (None, "en"), ("", "en")],
)
def test_base_language(code, expected):
    assert bot.base_language(code) == expected


def test_target_language_uses_telegram_language():
    assert bot.target_language(make_user("de")) == "de"
    assert bot.target_language(make_user(None)) == "en"


def ctx(**data):
    return SimpleNamespace(user_data=dict(data))


def test_translation_mode_defaults_to_off():
    assert bot.translation_mode(ctx()) == "off"


@pytest.mark.parametrize(
    "data, expected",
    [
        ({"translate": True}, "system"),
        ({"translate": False}, "off"),
        ({"translate_mode": "custom", "translate": True}, "custom"),
        ({"translate_mode": "off", "translate": True}, "off"),
        ({"translate_mode": "bogus"}, "off"),
    ],
)
def test_translation_mode_migrates_old_flag(data, expected):
    assert bot.translation_mode(ctx(**data)) == expected


def test_translation_target():
    user = make_user("de")
    assert bot.translation_target(user, ctx()) is None
    assert bot.translation_target(user, ctx(translate_mode="system")) == "de"
    assert bot.translation_target(user, ctx(translate_mode="custom", translate_lang="es")) == "es"
    assert bot.translation_target(user, ctx(translate="x", translate_mode="custom")) == "de"


def test_with_translation_format():
    block = bot.translation_block(make_user("ru"), "привет", "ru")
    assert block == "🌐 Перевод (русский):\nпривет"
    assert bot.with_translation("hi", block) == "hi\n\n🌐 Перевод (русский):\nпривет"


def test_translation_header_follows_ui_language():
    assert bot.translation_block(make_user("en"), "hi", "en") == "🌐 Translation (English):\nhi"


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


def buttons(markup):
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


def test_settings_keyboard_opens_translate_menu():
    assert buttons(bot.settings_keyboard(make_user("ru"))) == [("🌐 Перевод", "menu:translate")]


@pytest.mark.parametrize(
    "data, checked",
    [
        ({}, "tmode:off"),
        ({"translate_mode": "system"}, "tmode:system"),
        ({"translate_mode": "custom", "translate_lang": "de"}, "tmode:custom"),
    ],
)
def test_translate_menu_marks_current_mode(data, checked):
    markup = bot.translate_menu_keyboard(make_user("ru"), ctx(**data))
    assert all(len(row) == 1 for row in markup.inline_keyboard)
    marked = [d for text, d in buttons(markup) if text.startswith("✅ ")]
    assert marked == [checked]
    assert buttons(markup)[-1] == ("« Назад", "menu:main")


def test_translate_menu_texts():
    markup = bot.translate_menu_keyboard(
        make_user("ru"), ctx(translate_mode="custom", translate_lang="de")
    )
    assert buttons(markup) == [
        ("На язык системы (русский)", "tmode:system"),
        ("✅ На немецкий…", "tmode:custom"),
        ("Не переводить", "tmode:off"),
        ("« Назад", "menu:main"),
    ]
    markup = bot.translate_menu_keyboard(make_user("ru"), ctx())
    assert buttons(markup)[1] == ("На другой язык…", "tmode:custom")


def test_settings_text_shows_status():
    user = make_user("ru")
    assert bot.settings_text(user, ctx()) == "Настройки\n\nПеревод: выключен"
    assert bot.settings_text(user, ctx(translate_mode="system")).endswith(
        "Перевод: на язык системы (русский)"
    )
    assert bot.settings_text(user, ctx(translate_mode="custom", translate_lang="de")).endswith(
        "Перевод: на немецкий"
    )


def test_reply_keyboard_is_persistent_settings_button():
    markup = bot.reply_keyboard(make_user("en"))
    assert markup.keyboard[0][0].text == "⚙️ Settings"
    assert markup.is_persistent is True
    assert markup.resize_keyboard is True


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

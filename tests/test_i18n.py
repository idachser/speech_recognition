import asyncio
from unittest.mock import AsyncMock

import pytest
from telegram.error import TelegramError

import bot
import i18n


def test_all_languages_have_the_same_keys():
    reference = set(i18n.TEXTS["ru"])
    for lang, texts in i18n.TEXTS.items():
        assert set(texts) == reference, lang


@pytest.mark.parametrize(
    "code, expected",
    [
        ("ru", "ru"),
        ("en", "en"),
        ("en-GB", "en"),
        ("uk", "uk"),
        ("de", "de"),
        ("pt-br", "pt"),
        ("zh-hans", "zh"),
        ("ja", "en"),
        (None, "en"),
        ("", "en"),
    ],
)
def test_ui_language(code, expected):
    assert i18n.ui_language(code) == expected


def test_t_formats_placeholders():
    assert i18n.t("en", "translation_header", lang="de") == "🌐 Translation (de):"
    assert i18n.t("ja", "start", name="Alex").startswith("Hi, Alex!")


def test_new_languages_translate_button():
    assert i18n.t("de", "translate_button") == "Übersetzen"
    assert i18n.t("es-419", "translate_button") == "Traducir"


@pytest.mark.parametrize("lang", list(i18n.TEXTS))
def test_every_text_formats(lang):
    for key, template in i18n.TEXTS[lang].items():
        template.format(name="Alex", lang="xx")


def test_bot_commands_are_localized():
    assert [(c.command, c.description) for c in bot.bot_commands("uk")] == [
        ("start", "Почати"),
        ("settings", "Налаштування перекладу"),
    ]


def fake_bot(set_my_commands):
    return type("Bot", (), {"set_my_commands": set_my_commands})()


async def test_publish_commands_registers_default_and_each_language():
    set_my_commands = AsyncMock()
    await bot.publish_commands(fake_bot(set_my_commands))

    calls = set_my_commands.await_args_list
    assert calls[0].kwargs == {}
    assert [c.kwargs["language_code"] for c in calls[1:]] == list(i18n.TEXTS)


async def test_set_commands_retries_until_success(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(bot.asyncio, "sleep", sleep)
    publish = AsyncMock(side_effect=[TelegramError("Timed out"), TelegramError("Timed out"), None])
    monkeypatch.setattr(bot, "publish_commands", publish)

    assert await bot.set_commands_with_retry(object(), attempts=5, delay=7) is True
    assert publish.await_count == 3
    assert [c.args for c in sleep.await_args_list] == [(7,), (7,)]


async def test_set_commands_gives_up_without_raising(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(bot.asyncio, "sleep", sleep)
    publish = AsyncMock(side_effect=TelegramError("Too Many Requests"))
    monkeypatch.setattr(bot, "publish_commands", publish)

    assert await bot.set_commands_with_retry(object(), attempts=3, delay=1) is False
    assert publish.await_count == 3
    assert sleep.await_count == 2


async def test_set_commands_runs_in_background(monkeypatch):
    publish = AsyncMock()
    monkeypatch.setattr(bot, "publish_commands", publish)
    app = type("App", (), {"bot": object()})()

    await bot.set_commands(app)
    assert len(bot._background_tasks) == 1
    await asyncio.gather(*bot._background_tasks)

    publish.assert_awaited_once()
    assert not bot._background_tasks

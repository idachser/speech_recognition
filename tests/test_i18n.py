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


async def test_set_commands_registers_default_and_each_language():
    set_my_commands = AsyncMock()
    app = type("App", (), {"bot": type("Bot", (), {"set_my_commands": set_my_commands})()})()
    await bot.set_commands(app)

    calls = set_my_commands.await_args_list
    assert calls[0].kwargs == {}
    assert [c.kwargs["language_code"] for c in calls[1:]] == list(i18n.TEXTS)


async def test_set_commands_failure_does_not_crash():
    set_my_commands = AsyncMock(side_effect=TelegramError("Too Many Requests"))
    app = type("App", (), {"bot": type("Bot", (), {"set_my_commands": set_my_commands})()})()
    await bot.set_commands(app)

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot
from conftest import make_message, make_transcript, make_user


def voice_update(language_code="ru"):
    return SimpleNamespace(message=make_message(), effective_user=make_user(language_code))


def callback_update(data, message, language_code="ru"):
    query = SimpleNamespace(
        data=data,
        message=message,
        from_user=make_user(language_code),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    return SimpleNamespace(callback_query=query)


@pytest.fixture
def transcribe_returns(monkeypatch):
    calls = []

    def setup(transcript=None, error=None):
        def fake(url, translate_to):
            calls.append((url, translate_to))
            if error:
                raise error
            return transcript

        monkeypatch.setattr(bot, "transcribe", fake)
        return calls

    return setup


def sent(update):
    call = update.message.reply_text.await_args
    return call.args[0], call.kwargs.get("reply_markup")


def buttons(markup):
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


def text_update(text, language_code="ru"):
    return SimpleNamespace(
        message=make_message(text=text), effective_user=make_user(language_code)
    )


async def test_start_mentions_settings_button_and_sends_reply_keyboard(context):
    update = voice_update()
    await bot.start(update, context)
    text, markup = sent(update)
    assert "Alex" in text
    assert "⚙️ Настройки" in text
    assert markup.keyboard[0][0].text == "⚙️ Настройки"
    assert markup.is_persistent is True


async def test_settings_command_shows_main_screen(context):
    context.user_data["translate_mode"] = "custom"
    context.user_data["translate_lang"] = "de"
    context.user_data["awaiting_language"] = True
    update = voice_update("ru")
    await bot.settings(update, context)

    text, markup = sent(update)
    assert text == "Настройки\n\nПеревод: на немецкий"
    assert buttons(markup) == [("🌐 Перевод", "menu:translate")]
    assert context.user_data["awaiting_language"] is False


async def test_menu_translate_shows_submenu(context):
    update = callback_update("menu:translate", make_message())
    await bot.handle_menu(update, context)

    call = update.callback_query.edit_message_text.await_args
    assert [d for _, d in buttons(call.kwargs["reply_markup"])] == [
        "tmode:system",
        "tmode:custom",
        "tmode:off",
        "menu:main",
    ]


async def test_menu_main_resets_waiting_and_shows_main_screen(context):
    context.user_data["awaiting_language"] = True
    update = callback_update("menu:main", make_message())
    await bot.handle_menu(update, context)

    call = update.callback_query.edit_message_text.await_args
    assert context.user_data["awaiting_language"] is False
    assert call.args[0] == "Настройки\n\nПеревод: выключен"
    assert buttons(call.kwargs["reply_markup"]) == [("🌐 Перевод", "menu:translate")]


@pytest.mark.parametrize("mode", ["system", "off"])
async def test_tmode_saves_mode_and_returns_to_main(context, mode):
    context.user_data["awaiting_language"] = True
    update = callback_update(f"tmode:{mode}", make_message())
    await bot.handle_mode(update, context)

    query = update.callback_query
    assert context.user_data["translate_mode"] == mode
    assert context.user_data["awaiting_language"] is False
    query.answer.assert_awaited_once_with("Сохранено")
    assert query.edit_message_text.await_args.args[0].startswith("Настройки")


async def test_tmode_custom_asks_for_language(context):
    update = callback_update("tmode:custom", make_message())
    await bot.handle_mode(update, context)

    call = update.callback_query.edit_message_text.await_args
    assert context.user_data["awaiting_language"] is True
    assert "немецкий" in call.args[0]
    assert buttons(call.kwargs["reply_markup"]) == [("Отмена", "menu:main")]
    assert "translate_mode" not in context.user_data


async def test_custom_language_flow(context):
    await bot.handle_mode(callback_update("tmode:custom", make_message()), context)

    update = text_update("немецкий")
    await bot.handle_text(update, context)

    assert context.user_data["translate_mode"] == "custom"
    assert context.user_data["translate_lang"] == "de"
    assert context.user_data["awaiting_language"] is False
    texts = [c.args[0] for c in update.message.reply_text.await_args_list]
    assert texts == ["Готово, перевожу на немецкий.", "Настройки\n\nПеревод: на немецкий"]


async def test_unknown_language_keeps_waiting(context):
    context.user_data["awaiting_language"] = True
    update = text_update("абракадабра")
    await bot.handle_text(update, context)

    assert sent(update) == ("Не знаю такой язык, попробуй ещё раз.", None)
    assert context.user_data["awaiting_language"] is True
    assert "translate_mode" not in context.user_data


async def test_settings_button_in_another_language_opens_settings(context):
    context.user_data["awaiting_language"] = True
    update = text_update("⚙️ Settings", language_code="ru")
    await bot.handle_text(update, context)

    text, markup = sent(update)
    assert text.startswith("Настройки")
    assert buttons(markup) == [("🌐 Перевод", "menu:translate")]
    assert context.user_data["awaiting_language"] is False


async def test_stray_text_gets_hint_with_reply_keyboard(context):
    update = text_update("привет")
    await bot.handle_text(update, context)

    text, markup = sent(update)
    assert text == "Пришли голосовое, настройки под кнопкой ниже."
    assert markup.keyboard[0][0].text == "⚙️ Настройки"


@pytest.mark.parametrize(
    "data, mode", [("settings:on", "system"), ("settings:off", "off")]
)
async def test_legacy_settings_buttons_still_work(context, data, mode):
    update = callback_update(data, make_message())
    await bot.handle_legacy_settings(update, context)

    assert context.user_data["translate_mode"] == mode
    update.callback_query.edit_message_text.assert_awaited_once()


async def test_voice_same_language_has_no_button(context, transcribe_returns):
    calls = transcribe_returns(make_transcript(text="привет", language_code="ru"))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert calls == [("https://file", None)]
    assert sent(update) == ("привет", None)


async def test_voice_foreign_with_translation_off_offers_button(context, transcribe_returns):
    transcribe_returns(make_transcript(text="hello", language_code="en", transcript_id="abc"))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    text, markup = sent(update)
    assert text == "hello"
    button = markup.inline_keyboard[0][0]
    assert (button.text, button.callback_data) == ("Перевести", "tr:ru:abc")


async def test_voice_uses_audio_when_no_voice(context, transcribe_returns):
    transcribe_returns(make_transcript(language_code="ru"))
    update = voice_update()
    update.message.voice = None
    update.message.audio = SimpleNamespace(file_id="audio-id")
    await bot.handle_voice(update, context)

    context.bot.get_file.assert_awaited_once_with("audio-id")


async def test_voice_with_translation_on_replies_with_both(context, transcribe_returns):
    context.user_data["translate_mode"] = "system"
    calls = transcribe_returns(
        make_transcript(text="hello", language_code="en", translated_texts={"ru": "привет"})
    )
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert calls == [("https://file", "ru")]
    assert sent(update) == ("hello\n\n🌐 Перевод (русский):\nпривет", None)


async def test_voice_translation_missing_falls_back_to_button(context, transcribe_returns):
    context.user_data["translate_mode"] = "system"
    transcribe_returns(make_transcript(text="hello", language_code="en", translated_texts={}))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    text, markup = sent(update)
    assert text == "hello"
    assert markup.inline_keyboard[0][0].callback_data == "tr:ru:t-1"


async def test_voice_long_translation_is_sent_separately(context, transcribe_returns):
    context.user_data["translate_mode"] = "system"
    original = "a" * 3000
    translation = "б" * 3000
    transcribe_returns(
        make_transcript(text=original, language_code="en", translated_texts={"ru": translation})
    )
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    texts = [c.args[0] for c in update.message.reply_text.await_args_list]
    assert texts == [original, f"🌐 Перевод (русский):\n{translation}"]


async def test_voice_undetected_language_is_not_treated_as_foreign(context, transcribe_returns):
    transcribe_returns(make_transcript(text="hmm", language_code=None))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert sent(update) == ("hmm", None)


async def test_voice_empty_text(context, transcribe_returns):
    transcribe_returns(make_transcript(text=""))
    update = voice_update()
    await bot.handle_voice(update, context)

    assert sent(update) == ("Не удалось распознать речь.", None)


async def test_voice_transcription_error(context, transcribe_returns):
    transcribe_returns(error=RuntimeError("boom"))
    update = voice_update()
    await bot.handle_voice(update, context)

    assert sent(update) == ("Не удалось распознать, попробуй еще раз.", None)


async def test_translate_button_edits_message(context, monkeypatch):
    calls = []

    def fake(transcript_id, lang):
        calls.append((transcript_id, lang))
        return "привет"

    monkeypatch.setattr(bot, "translate_existing", fake)
    update = callback_update("tr:abc", make_message(text="hello"), language_code="ru")
    await bot.handle_translate(update, context)

    query = update.callback_query
    assert calls == [("abc", "ru")]
    query.answer.assert_awaited_once_with()
    query.edit_message_text.assert_awaited_once_with("hello\n\n🌐 Перевод (русский):\nпривет")


@pytest.mark.parametrize("outcome", [None, RuntimeError("boom")])
async def test_translate_button_failure_shows_alert(context, monkeypatch, outcome):
    def fake(transcript_id, lang):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(bot, "translate_existing", fake)
    update = callback_update("tr:abc", make_message(text="hello"))
    await bot.handle_translate(update, context)

    query = update.callback_query
    query.answer.assert_awaited_once_with("Не удалось перевести", show_alert=True)
    query.edit_message_text.assert_not_awaited()


async def test_translate_button_long_text_replies_separately(context, monkeypatch):
    translation = "б" * 3000
    monkeypatch.setattr(bot, "translate_existing", lambda transcript_id, lang: translation)
    message = make_message(text="a" * 3000)
    update = callback_update("tr:abc", message)
    await bot.handle_translate(update, context)

    query = update.callback_query
    query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
    query.edit_message_text.assert_not_awaited()
    assert message.reply_text.await_args.args[0] == f"🌐 Перевод (русский):\n{translation}"


async def test_voice_legacy_translate_flag_still_translates(context, transcribe_returns):
    context.user_data["translate"] = True
    calls = transcribe_returns(
        make_transcript(text="hello", language_code="en", translated_texts={"ru": "привет"})
    )
    await bot.handle_voice(voice_update("ru"), context)

    assert calls == [("https://file", "ru")]


async def test_voice_custom_language_translates_to_it(context, transcribe_returns):
    context.user_data.update(translate_mode="custom", translate_lang="es")
    calls = transcribe_returns(
        make_transcript(text="hello", language_code="en", translated_texts={"es": "hola"})
    )
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert calls == [("https://file", "es")]
    assert sent(update) == ("hello\n\n🌐 Перевод (испанский):\nhola", None)


async def test_voice_custom_language_foreign_is_relative_to_target(context, transcribe_returns):
    context.user_data.update(translate_mode="custom", translate_lang="es")
    transcribe_returns(make_transcript(text="hola", language_code="es"))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert sent(update) == ("hola", None)


async def test_voice_custom_language_missing_translation_offers_button_for_target(
    context, transcribe_returns
):
    context.user_data.update(translate_mode="custom", translate_lang="es")
    transcribe_returns(make_transcript(text="hello", language_code="en", translated_texts={}))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    _, markup = sent(update)
    assert markup.inline_keyboard[0][0].callback_data == "tr:es:t-1"


async def test_translate_button_with_language_in_callback(context, monkeypatch):
    calls = []

    def fake(transcript_id, lang):
        calls.append((transcript_id, lang))
        return "hallo"

    monkeypatch.setattr(bot, "translate_existing", fake)
    update = callback_update("tr:de:abc", make_message(text="hello"), language_code="ru")
    await bot.handle_translate(update, context)

    assert calls == [("abc", "de")]
    update.callback_query.edit_message_text.assert_awaited_once_with(
        "hello\n\n🌐 Перевод (немецкий):\nhallo"
    )


async def test_start_in_english(context):
    update = voice_update("en")
    await bot.start(update, context)
    assert update.message.reply_text.await_args.args[0].startswith("Hi, Alex!")


async def test_unknown_language_falls_back_to_english(context, transcribe_returns):
    transcribe_returns(make_transcript(text="hallo", language_code="en"))
    update = voice_update("ja")
    await bot.handle_voice(update, context)

    _, markup = sent(update)
    assert markup.inline_keyboard[0][0].text == "Translate"


async def test_error_message_in_users_language(context, transcribe_returns):
    transcribe_returns(error=RuntimeError("boom"))
    update = voice_update("uk")
    await bot.handle_voice(update, context)

    assert sent(update) == ("Не вдалося розпізнати, спробуй ще раз.", None)


async def test_translate_button_header_in_users_language(context, monkeypatch):
    monkeypatch.setattr(bot, "translate_existing", lambda transcript_id, lang: "hello")
    update = callback_update("tr:abc", make_message(text="привет"), language_code="en")
    await bot.handle_translate(update, context)

    update.callback_query.edit_message_text.assert_awaited_once_with(
        "привет\n\n🌐 Translation (English):\nhello"
    )


async def test_missing_language_code_defaults_to_english(context, transcribe_returns):
    transcribe_returns(make_transcript(text="привет", language_code="ru"))
    update = voice_update(None)
    await bot.handle_voice(update, context)

    _, markup = sent(update)
    assert markup.inline_keyboard[0][0].text == "Translate"

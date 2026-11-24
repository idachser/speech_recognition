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


async def test_start_mentions_settings(context):
    update = voice_update()
    await bot.start(update, context)
    text = update.message.reply_text.await_args.args[0]
    assert "Alex" in text
    assert "/settings" in text


async def test_settings_shows_current_choice(context):
    context.user_data["translate"] = True
    update = voice_update("en")
    await bot.settings(update, context)

    call = update.message.reply_text.await_args
    assert "(en)" in call.args[0]
    assert call.kwargs["reply_markup"] == bot.settings_keyboard(make_user("en"), True)


async def test_handle_settings_saves_choice_and_updates_keyboard(context):
    update = callback_update("settings:on", make_message(reply_markup=bot.settings_keyboard(make_user(), False)))
    await bot.handle_settings(update, context)

    query = update.callback_query
    assert context.user_data["translate"] is True
    query.answer.assert_awaited_once_with("Перевод включён")
    assert query.edit_message_text.await_args.kwargs["reply_markup"] == bot.settings_keyboard(make_user(), True)


async def test_handle_settings_skips_edit_when_unchanged(context):
    context.user_data["translate"] = False
    update = callback_update("settings:off", make_message(reply_markup=bot.settings_keyboard(make_user(), False)))
    await bot.handle_settings(update, context)

    assert context.user_data["translate"] is False
    update.callback_query.answer.assert_awaited_once_with("Перевод выключен")
    update.callback_query.edit_message_text.assert_not_awaited()


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
    assert (button.text, button.callback_data) == ("Перевести", "tr:abc")


async def test_voice_uses_audio_when_no_voice(context, transcribe_returns):
    transcribe_returns(make_transcript(language_code="ru"))
    update = voice_update()
    update.message.voice = None
    update.message.audio = SimpleNamespace(file_id="audio-id")
    await bot.handle_voice(update, context)

    context.bot.get_file.assert_awaited_once_with("audio-id")


async def test_voice_with_translation_on_replies_with_both(context, transcribe_returns):
    context.user_data["translate"] = True
    calls = transcribe_returns(
        make_transcript(text="hello", language_code="en", translated_texts={"ru": "привет"})
    )
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    assert calls == [("https://file", "ru")]
    assert sent(update) == ("hello\n\n🌐 Перевод (ru):\nпривет", None)


async def test_voice_translation_missing_falls_back_to_button(context, transcribe_returns):
    context.user_data["translate"] = True
    transcribe_returns(make_transcript(text="hello", language_code="en", translated_texts={}))
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    text, markup = sent(update)
    assert text == "hello"
    assert markup.inline_keyboard[0][0].callback_data == "tr:t-1"


async def test_voice_long_translation_is_sent_separately(context, transcribe_returns):
    context.user_data["translate"] = True
    original = "a" * 3000
    translation = "б" * 3000
    transcribe_returns(
        make_transcript(text=original, language_code="en", translated_texts={"ru": translation})
    )
    update = voice_update("ru")
    await bot.handle_voice(update, context)

    texts = [c.args[0] for c in update.message.reply_text.await_args_list]
    assert texts == [original, f"🌐 Перевод (ru):\n{translation}"]


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
    query.edit_message_text.assert_awaited_once_with("hello\n\n🌐 Перевод (ru):\nпривет")


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
    assert message.reply_text.await_args.args[0] == f"🌐 Перевод (ru):\n{translation}"


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
        "привет\n\n🌐 Translation (en):\nhello"
    )


async def test_missing_language_code_defaults_to_english(context, transcribe_returns):
    transcribe_returns(make_transcript(text="привет", language_code="ru"))
    update = voice_update(None)
    await bot.handle_voice(update, context)

    _, markup = sent(update)
    assert markup.inline_keyboard[0][0].text == "Translate"

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.constants import ChatAction
from telegram.error import TelegramError

import bot
from conftest import make_message, make_transcript, make_user


def typing_bot(side_effect=None):
    return SimpleNamespace(send_chat_action=AsyncMock(side_effect=side_effect))


async def test_typing_action_repeats_while_waiting():
    fake = typing_bot()
    async with bot.typing_action(fake, 42, interval=0.01):
        await asyncio.sleep(0.035)

    calls = fake.send_chat_action.await_args_list
    assert len(calls) >= 3
    assert all(c.args == (42, ChatAction.TYPING) for c in calls)


async def test_typing_action_stops_after_exit():
    fake = typing_bot()
    async with bot.typing_action(fake, 42, interval=0.01):
        await asyncio.sleep(0)
    count = fake.send_chat_action.await_count

    await asyncio.sleep(0.03)
    assert fake.send_chat_action.await_count == count


async def test_typing_action_swallows_telegram_errors():
    fake = typing_bot(side_effect=TelegramError("Too Many Requests"))
    done = False
    async with bot.typing_action(fake, 42, interval=0.01):
        await asyncio.sleep(0.025)
        done = True

    assert done
    assert fake.send_chat_action.await_count >= 2


async def test_typing_action_cancels_on_exception_in_body():
    fake = typing_bot()
    with pytest.raises(RuntimeError, match="boom"):
        async with bot.typing_action(fake, 42, interval=0.01):
            await asyncio.sleep(0)
            raise RuntimeError("boom")
    count = fake.send_chat_action.await_count

    await asyncio.sleep(0.03)
    assert fake.send_chat_action.await_count == count


async def test_voice_shows_typing_while_transcribing(context, monkeypatch):
    def slow_transcribe(url, translate_to):
        time.sleep(0.05)
        return make_transcript(text="привет", language_code="ru")

    monkeypatch.setattr(bot, "transcribe", slow_transcribe)
    update = SimpleNamespace(message=make_message(), effective_user=make_user("ru"))
    await bot.handle_voice(update, context)

    context.bot.send_chat_action.assert_awaited_with(42, ChatAction.TYPING)
    update.message.reply_text.assert_awaited_once()


async def test_translate_button_shows_typing(context, monkeypatch):
    def slow_translate(transcript_id, lang):
        time.sleep(0.05)
        return "привет"

    monkeypatch.setattr(bot, "translate_existing", slow_translate)
    query = SimpleNamespace(
        data="tr:ru:abc",
        message=make_message(text="hello"),
        from_user=make_user("ru"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    await bot.handle_translate(SimpleNamespace(callback_query=query), context)

    context.bot.send_chat_action.assert_awaited_with(42, ChatAction.TYPING)
    query.edit_message_text.assert_awaited_once()

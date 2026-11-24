import asyncio
import logging
import os

import assemblyai as aai
from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import MessageLimit
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from i18n import TEXTS, base_language, t


logger = logging.getLogger(__name__)

MAX_LEN = MessageLimit.MAX_TEXT_LENGTH


def tr(user: User, key: str, **kwargs) -> str:
    return t(user.language_code, key, **kwargs)


def target_language(user: User) -> str:
    return base_language(user.language_code)


def translate_enabled(context: CallbackContext) -> bool:
    return context.user_data.get("translate", False)


def translation_block(user: User, translation: str, lang: str) -> str:
    return f"{tr(user, 'translation_header', lang=lang)}\n{translation}"


def with_translation(original: str, block: str) -> str:
    return f"{original}\n\n{block}"


def chunks(text: str) -> list[str]:
    return [text[i : i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]


async def reply_long(message, text: str, reply_markup=None) -> None:
    parts = chunks(text)
    for i, part in enumerate(parts):
        markup = reply_markup if i == len(parts) - 1 else None
        await message.reply_text(part, reply_markup=markup)


def transcribe(file_url: str, translate_to: str | None) -> aai.Transcript:
    speech_understanding = None
    if translate_to:
        speech_understanding = aai.SpeechUnderstandingRequest(
            request=aai.SpeechUnderstandingFeatureRequests(
                translation=aai.TranslationRequest(target_languages=[translate_to])
            )
        )
    config = aai.TranscriptionConfig(
        language_detection=True,
        speech_understanding=speech_understanding,
    )
    transcript = aai.Transcriber(config=config).transcribe(file_url)
    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(transcript.error)
    return transcript


def translate_existing(transcript_id: str, lang: str) -> str | None:
    response = aai.LLMGateway().understanding.create(
        transcript_id=transcript_id,
        request={"translation": {"target_languages": [lang]}},
    )
    return (response.translated_texts or {}).get(lang)


def settings_keyboard(user: User, enabled: bool) -> InlineKeyboardMarkup:
    on = ("✅ " if enabled else "") + tr(user, "translate_on")
    off = ("" if enabled else "✅ ") + tr(user, "translate_off")
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(on, callback_data="settings:on"),
                InlineKeyboardButton(off, callback_data="settings:off"),
            ]
        ]
    )


def settings_text(user: User) -> str:
    return tr(user, "settings", lang=target_language(user))


async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(tr(user, "start", name=user.first_name))


async def settings(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(
        settings_text(user),
        reply_markup=settings_keyboard(user, translate_enabled(context)),
    )


async def handle_settings(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user = query.from_user
    enabled = query.data == "settings:on"
    context.user_data["translate"] = enabled
    await query.answer(tr(user, "translate_enabled" if enabled else "translate_disabled"))
    keyboard = settings_keyboard(user, enabled)
    if query.message.reply_markup != keyboard:
        await query.edit_message_text(settings_text(user), reply_markup=keyboard)


async def handle_voice(update: Update, context: CallbackContext) -> None:
    message = update.message
    user = update.effective_user
    try:
        media = message.voice or message.audio
        new_file = await context.bot.get_file(media.file_id)

        lang = target_language(user)
        auto_translate = translate_enabled(context)
        transcript = await asyncio.to_thread(
            transcribe, new_file.file_path, lang if auto_translate else None
        )

        if not transcript.text:
            await message.reply_text(tr(user, "no_speech"))
            return

        detected = transcript.language_code
        foreign = bool(detected) and base_language(detected) != lang

        if auto_translate and foreign:
            translation = (transcript.translated_texts or {}).get(lang)
            if translation:
                block = translation_block(user, translation, lang)
                combined = with_translation(transcript.text, block)
                if len(combined) <= MAX_LEN:
                    await message.reply_text(combined)
                else:
                    await reply_long(message, transcript.text)
                    await reply_long(message, block)
                return

        markup = None
        if foreign:
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            tr(user, "translate_button"),
                            callback_data=f"tr:{transcript.id}",
                        )
                    ]
                ]
            )
        await reply_long(message, transcript.text, reply_markup=markup)

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        await message.reply_text(tr(user, "transcription_failed"))


async def handle_translate(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user = query.from_user
    transcript_id = query.data.removeprefix("tr:")
    lang = target_language(user)

    try:
        translation = await asyncio.to_thread(translate_existing, transcript_id, lang)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        translation = None

    if not translation:
        await query.answer(tr(user, "translation_failed"), show_alert=True)
        return

    await query.answer()
    block = translation_block(user, translation, lang)
    combined = with_translation(query.message.text, block)
    if len(combined) <= MAX_LEN:
        await query.edit_message_text(combined)
    else:
        await query.edit_message_reply_markup(reply_markup=None)
        await reply_long(query.message, block)


def bot_commands(code: str | None) -> list[BotCommand]:
    return [
        BotCommand("start", t(code, "cmd_start")),
        BotCommand("settings", t(code, "cmd_settings")),
    ]


async def set_commands(app: Application) -> None:
    # post_init runs outside the bootstrap retry loop, so a failure here would
    # crash the bot; the command menu is cosmetic and must not.
    try:
        await app.bot.set_my_commands(bot_commands("en"))
        for lang in TEXTS:
            await app.bot.set_my_commands(bot_commands(lang), language_code=lang)
    except TelegramError as e:
        logger.warning(f"Could not set bot commands: {e}")


def main() -> None:
    persistence = PicklePersistence(filepath="bot_data.pickle")
    app = (
        Application.builder()
        .token(telegram_token)
        .persistence(persistence)
        .post_init(set_commands)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(
        CallbackQueryHandler(handle_settings, pattern=r"^settings:(on|off)$")
    )
    app.add_handler(CallbackQueryHandler(handle_translate, pattern=r"^tr:", block=False))
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO),
            handle_voice,
            block=False,
        )
    )

    # Without retries a startup TimedOut kills the process, and the container
    # restart loop then hammers getMe until Telegram answers with RetryAfter.
    app.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        filename="enotebot.log",
        filemode="w",
    )
    # httpx logs every request URL at INFO, and Telegram URLs contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv()
    aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    telegram_token = os.environ.get("TELEGRAM_API_TOKEN")

    main()

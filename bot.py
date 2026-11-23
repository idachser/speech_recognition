import asyncio
import logging
import os

import assemblyai as aai
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import MessageLimit
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)


logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "ru"
MAX_LEN = MessageLimit.MAX_TEXT_LENGTH


def base_language(code: str | None) -> str:
    if not code:
        return DEFAULT_LANGUAGE
    return code.replace("_", "-").split("-")[0].lower()


def target_language(user: User) -> str:
    return base_language(user.language_code)


def translate_enabled(context: CallbackContext) -> bool:
    return context.user_data.get("translate", False)


def with_translation(original: str, translation: str, lang: str) -> str:
    return f"{original}\n\n🌐 Перевод ({lang}):\n{translation}"


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


def settings_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    on = ("✅ " if enabled else "") + "Переводить"
    off = ("" if enabled else "✅ ") + "Не переводить"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(on, callback_data="settings:on"),
                InlineKeyboardButton(off, callback_data="settings:off"),
            ]
        ]
    )


def settings_text(user: User) -> str:
    return (
        "Переводить расшифровки на язык твоего Telegram "
        f"({target_language(user)}), если голосовое на другом языке?"
    )


async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Я бот для распознавания голосовых сообщений в текст. "
        "Присылай мне свои голосовые на любом языке.\n\n"
        "В /settings можно включить автоматический перевод.\n\n"
        "Я ничего не записываю и не храню.)"
    )


async def settings(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        settings_text(update.effective_user),
        reply_markup=settings_keyboard(translate_enabled(context)),
    )


async def handle_settings(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    enabled = query.data == "settings:on"
    context.user_data["translate"] = enabled
    await query.answer("Перевод включён" if enabled else "Перевод выключен")
    if query.message.reply_markup != settings_keyboard(enabled):
        await query.edit_message_text(
            settings_text(query.from_user),
            reply_markup=settings_keyboard(enabled),
        )


async def handle_voice(update: Update, context: CallbackContext) -> None:
    message = update.message
    try:
        media = message.voice or message.audio
        new_file = await context.bot.get_file(media.file_id)

        lang = target_language(update.effective_user)
        auto_translate = translate_enabled(context)
        transcript = await asyncio.to_thread(
            transcribe, new_file.file_path, lang if auto_translate else None
        )

        if not transcript.text:
            await message.reply_text("Не удалось распознать речь.")
            return

        detected = transcript.language_code
        foreign = bool(detected) and base_language(detected) != lang

        if auto_translate and foreign:
            translation = (transcript.translated_texts or {}).get(lang)
            if translation:
                combined = with_translation(transcript.text, translation, lang)
                if len(combined) <= MAX_LEN:
                    await message.reply_text(combined)
                else:
                    await reply_long(message, transcript.text)
                    await reply_long(message, f"🌐 Перевод ({lang}):\n{translation}")
                return

        markup = None
        if foreign:
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Перевести", callback_data=f"tr:{transcript.id}")]]
            )
        await reply_long(message, transcript.text, reply_markup=markup)

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        await message.reply_text("Не удалось распознать, попробуй еще раз.")


async def handle_translate(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    transcript_id = query.data.removeprefix("tr:")
    lang = target_language(query.from_user)

    try:
        translation = await asyncio.to_thread(translate_existing, transcript_id, lang)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        translation = None

    if not translation:
        await query.answer("Не удалось перевести", show_alert=True)
        return

    await query.answer()
    combined = with_translation(query.message.text, translation, lang)
    if len(combined) <= MAX_LEN:
        await query.edit_message_text(combined)
    else:
        await query.edit_message_reply_markup(reply_markup=None)
        await reply_long(query.message, f"🌐 Перевод ({lang}):\n{translation}")


def main() -> None:
    persistence = PicklePersistence(filepath="bot_data.pickle")
    app = (
        Application.builder()
        .token(telegram_token)
        .persistence(persistence)
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

    app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        filename="enotebot.log",
        filemode="w",
    )
    load_dotenv()
    aai.settings.api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    telegram_token = os.environ.get("TELEGRAM_API_TOKEN")

    main()

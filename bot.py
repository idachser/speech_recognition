import asyncio
import logging
import os

import assemblyai as aai
from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
    User,
)
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
from languages import language_name, resolve_language


logger = logging.getLogger(__name__)

MAX_LEN = MessageLimit.MAX_TEXT_LENGTH

MODES = ("off", "system", "custom")
SETTINGS_BUTTONS = {t(code, "settings_button") for code in TEXTS}


def tr(user: User, key: str, **kwargs) -> str:
    return t(user.language_code, key, **kwargs)


def target_language(user: User) -> str:
    return base_language(user.language_code)


def translation_mode(context: CallbackContext) -> str:
    mode = context.user_data.get("translate_mode")
    if mode in MODES:
        return mode
    return "system" if context.user_data.get("translate") else "off"


def translation_target(user: User, context: CallbackContext) -> str | None:
    mode = translation_mode(context)
    if mode == "system":
        return target_language(user)
    if mode == "custom":
        return context.user_data.get("translate_lang") or target_language(user)
    return None


def translation_block(user: User, translation: str, lang: str) -> str:
    name = language_name(lang, user.language_code)
    return f"{tr(user, 'translation_header', lang=name)}\n{translation}"


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


def reply_keyboard(user: User) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[tr(user, "settings_button")]], resize_keyboard=True, is_persistent=True
    )


def settings_text(user: User, context: CallbackContext) -> str:
    mode = translation_mode(context)
    if mode == "system":
        status = tr(user, "status_system", lang=language_name(target_language(user), user.language_code))
    elif mode == "custom":
        status = tr(user, "status_custom", lang=custom_language_name(user, context))
    else:
        status = tr(user, "status_off")
    return f"{tr(user, 'settings_title')}\n\n{status}"


def custom_language_name(user: User, context: CallbackContext) -> str:
    code = context.user_data.get("translate_lang") or target_language(user)
    return language_name(code, user.language_code)


def settings_keyboard(user: User) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(tr(user, "translate_menu_button"), callback_data="menu:translate")]]
    )


def translate_menu_keyboard(user: User, context: CallbackContext) -> InlineKeyboardMarkup:
    mode = translation_mode(context)
    system = tr(user, "mode_system", lang=language_name(target_language(user), user.language_code))
    if mode == "custom":
        custom = tr(user, "mode_custom_selected", lang=custom_language_name(user, context))
    else:
        custom = tr(user, "mode_custom")
    off = tr(user, "mode_off")
    rows = [
        [("✅ " if mode == "system" else "") + system, "tmode:system"],
        [("✅ " if mode == "custom" else "") + custom, "tmode:custom"],
        [("✅ " if mode == "off" else "") + off, "tmode:off"],
        [tr(user, "back"), "menu:main"],
    ]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data)] for text, data in rows]
    )


async def reply_settings(message, user: User, context: CallbackContext) -> None:
    await message.reply_text(
        settings_text(user, context), reply_markup=settings_keyboard(user)
    )


async def show_main(query, user: User, context: CallbackContext) -> None:
    await query.edit_message_text(
        settings_text(user, context), reply_markup=settings_keyboard(user)
    )


async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(
        tr(user, "start", name=user.first_name), reply_markup=reply_keyboard(user)
    )


async def settings(update: Update, context: CallbackContext) -> None:
    context.user_data["awaiting_language"] = False
    await reply_settings(update.message, update.effective_user, context)


async def handle_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user = query.from_user
    await query.answer()
    if query.data == "menu:translate":
        await query.edit_message_text(
            tr(user, "translate_menu_title"),
            reply_markup=translate_menu_keyboard(user, context),
        )
    else:
        context.user_data["awaiting_language"] = False
        await show_main(query, user, context)


async def handle_mode(update: Update, context: CallbackContext) -> None:
    await apply_mode(update.callback_query, context, update.callback_query.data.removeprefix("tmode:"))


async def apply_mode(query, context: CallbackContext, mode: str) -> None:
    user = query.from_user
    if mode == "custom":
        context.user_data["awaiting_language"] = True
        await query.answer()
        await query.edit_message_text(
            tr(user, "ask_language"),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(tr(user, "cancel"), callback_data="menu:main")]]
            ),
        )
        return

    context.user_data["translate_mode"] = mode
    context.user_data["awaiting_language"] = False
    await query.answer(tr(user, "mode_saved"))
    await show_main(query, user, context)


async def handle_legacy_settings(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await apply_mode(query, context, "system" if query.data == "settings:on" else "off")


async def handle_text(update: Update, context: CallbackContext) -> None:
    message = update.message
    user = update.effective_user
    text = message.text or ""

    if text.strip() in SETTINGS_BUTTONS:
        context.user_data["awaiting_language"] = False
        await reply_settings(message, user, context)
        return

    if context.user_data.get("awaiting_language"):
        code = resolve_language(text)
        if not code:
            await message.reply_text(tr(user, "language_unknown"))
            return
        context.user_data["translate_mode"] = "custom"
        context.user_data["translate_lang"] = code
        context.user_data["awaiting_language"] = False
        await message.reply_text(
            tr(user, "language_set", lang=language_name(code, user.language_code))
        )
        await reply_settings(message, user, context)
        return

    await message.reply_text(tr(user, "hint"), reply_markup=reply_keyboard(user))


async def handle_voice(update: Update, context: CallbackContext) -> None:
    message = update.message
    user = update.effective_user
    try:
        media = message.voice or message.audio
        new_file = await context.bot.get_file(media.file_id)

        target = translation_target(user, context)
        lang = target or target_language(user)
        transcript = await asyncio.to_thread(transcribe, new_file.file_path, target)

        if not transcript.text:
            await message.reply_text(tr(user, "no_speech"))
            return

        detected = transcript.language_code
        foreign = bool(detected) and base_language(detected) != lang

        if target and foreign:
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
                            callback_data=f"tr:{lang}:{transcript.id}",
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
    lang, _, transcript_id = query.data.removeprefix("tr:").rpartition(":")
    lang = lang or target_language(user)

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
    app.add_handler(CallbackQueryHandler(handle_menu, pattern=r"^menu:(main|translate)$"))
    app.add_handler(CallbackQueryHandler(handle_mode, pattern=r"^tmode:(system|custom|off)$"))
    app.add_handler(
        CallbackQueryHandler(handle_legacy_settings, pattern=r"^settings:(on|off)$")
    )
    app.add_handler(CallbackQueryHandler(handle_translate, pattern=r"^tr:", block=False))
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_text
        )
    )
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

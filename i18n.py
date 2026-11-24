DEFAULT_LANGUAGE = "en"

TEXTS = {
    "ru": {
        "start": (
            "Привет, {name}!\n\n"
            "Я бот для распознавания голосовых сообщений в текст. "
            "Присылай мне свои голосовые на любом языке.\n\n"
            "В /settings можно включить автоматический перевод.\n\n"
            "Я ничего не записываю и не храню.)"
        ),
        "settings": (
            "Переводить расшифровки на язык твоего Telegram ({lang}), "
            "если голосовое на другом языке?"
        ),
        "translate_on": "Переводить",
        "translate_off": "Не переводить",
        "translate_enabled": "Перевод включён",
        "translate_disabled": "Перевод выключен",
        "translate_button": "Перевести",
        "translation_header": "🌐 Перевод ({lang}):",
        "no_speech": "Не удалось распознать речь.",
        "transcription_failed": "Не удалось распознать, попробуй еще раз.",
        "translation_failed": "Не удалось перевести",
        "cmd_start": "Начать",
        "cmd_settings": "Настройки перевода",
    },
    "en": {
        "start": (
            "Hi, {name}!\n\n"
            "I turn voice messages into text. "
            "Send me your voice messages in any language.\n\n"
            "You can turn on automatic translation in /settings.\n\n"
            "I don't record or store anything.)"
        ),
        "settings": (
            "Translate transcripts into your Telegram language ({lang}) "
            "when a voice message is in another language?"
        ),
        "translate_on": "Translate",
        "translate_off": "Don't translate",
        "translate_enabled": "Translation on",
        "translate_disabled": "Translation off",
        "translate_button": "Translate",
        "translation_header": "🌐 Translation ({lang}):",
        "no_speech": "Couldn't recognize any speech.",
        "transcription_failed": "Couldn't transcribe this, please try again.",
        "translation_failed": "Couldn't translate",
        "cmd_start": "Start",
        "cmd_settings": "Translation settings",
    },
    "uk": {
        "start": (
            "Привіт, {name}!\n\n"
            "Я бот для розпізнавання голосових повідомлень у текст. "
            "Надсилай мені свої голосові будь-якою мовою.\n\n"
            "У /settings можна увімкнути автоматичний переклад.\n\n"
            "Я нічого не записую і не зберігаю.)"
        ),
        "settings": (
            "Перекладати розшифровки мовою твого Telegram ({lang}), "
            "якщо голосове іншою мовою?"
        ),
        "translate_on": "Перекладати",
        "translate_off": "Не перекладати",
        "translate_enabled": "Переклад увімкнено",
        "translate_disabled": "Переклад вимкнено",
        "translate_button": "Перекласти",
        "translation_header": "🌐 Переклад ({lang}):",
        "no_speech": "Не вдалося розпізнати мовлення.",
        "transcription_failed": "Не вдалося розпізнати, спробуй ще раз.",
        "translation_failed": "Не вдалося перекласти",
        "cmd_start": "Почати",
        "cmd_settings": "Налаштування перекладу",
    },
    "de": {
        "start": (
            "Hallo, {name}!\n\n"
            "Ich wandle Sprachnachrichten in Text um. "
            "Schick mir deine Sprachnachrichten in einer beliebigen Sprache.\n\n"
            "In /settings kannst du die automatische Übersetzung einschalten.\n\n"
            "Ich nehme nichts auf und speichere nichts.)"
        ),
        "settings": (
            "Transkripte in deine Telegram-Sprache ({lang}) übersetzen, "
            "wenn eine Sprachnachricht in einer anderen Sprache ist?"
        ),
        "translate_on": "Übersetzen",
        "translate_off": "Nicht übersetzen",
        "translate_enabled": "Übersetzung an",
        "translate_disabled": "Übersetzung aus",
        "translate_button": "Übersetzen",
        "translation_header": "🌐 Übersetzung ({lang}):",
        "no_speech": "Keine Sprache erkannt.",
        "transcription_failed": "Das konnte ich nicht erkennen, versuch es noch mal.",
        "translation_failed": "Konnte nicht übersetzt werden",
        "cmd_start": "Start",
        "cmd_settings": "Übersetzungseinstellungen",
    },
    "es": {
        "start": (
            "¡Hola, {name}!\n\n"
            "Convierto mensajes de voz en texto. "
            "Envíame tus mensajes de voz en cualquier idioma.\n\n"
            "En /settings puedes activar la traducción automática.\n\n"
            "No grabo ni guardo nada.)"
        ),
        "settings": (
            "¿Traducir las transcripciones a tu idioma de Telegram ({lang}) "
            "cuando un mensaje de voz esté en otro idioma?"
        ),
        "translate_on": "Traducir",
        "translate_off": "No traducir",
        "translate_enabled": "Traducción activada",
        "translate_disabled": "Traducción desactivada",
        "translate_button": "Traducir",
        "translation_header": "🌐 Traducción ({lang}):",
        "no_speech": "No se detectó voz.",
        "transcription_failed": "No se pudo transcribir, inténtalo de nuevo.",
        "translation_failed": "No se pudo traducir",
        "cmd_start": "Iniciar",
        "cmd_settings": "Ajustes de traducción",
    },
    "fr": {
        "start": (
            "Salut, {name} !\n\n"
            "Je transforme les messages vocaux en texte. "
            "Envoie-moi tes messages vocaux dans n'importe quelle langue.\n\n"
            "Tu peux activer la traduction automatique dans /settings.\n\n"
            "Je n'enregistre ni ne stocke rien.)"
        ),
        "settings": (
            "Traduire les transcriptions dans ta langue Telegram ({lang}) "
            "quand un message vocal est dans une autre langue ?"
        ),
        "translate_on": "Traduire",
        "translate_off": "Ne pas traduire",
        "translate_enabled": "Traduction activée",
        "translate_disabled": "Traduction désactivée",
        "translate_button": "Traduire",
        "translation_header": "🌐 Traduction ({lang}) :",
        "no_speech": "Aucune parole reconnue.",
        "transcription_failed": "Impossible de transcrire, réessaie.",
        "translation_failed": "Impossible de traduire",
        "cmd_start": "Démarrer",
        "cmd_settings": "Paramètres de traduction",
    },
    "it": {
        "start": (
            "Ciao, {name}!\n\n"
            "Trasformo i messaggi vocali in testo. "
            "Mandami i tuoi messaggi vocali in qualsiasi lingua.\n\n"
            "Puoi attivare la traduzione automatica in /settings.\n\n"
            "Non registro né conservo nulla.)"
        ),
        "settings": (
            "Tradurre le trascrizioni nella lingua del tuo Telegram ({lang}) "
            "quando un messaggio vocale è in un'altra lingua?"
        ),
        "translate_on": "Traduci",
        "translate_off": "Non tradurre",
        "translate_enabled": "Traduzione attiva",
        "translate_disabled": "Traduzione disattivata",
        "translate_button": "Traduci",
        "translation_header": "🌐 Traduzione ({lang}):",
        "no_speech": "Nessun parlato riconosciuto.",
        "transcription_failed": "Impossibile trascrivere, riprova.",
        "translation_failed": "Impossibile tradurre",
        "cmd_start": "Avvia",
        "cmd_settings": "Impostazioni di traduzione",
    },
    "pt": {
        "start": (
            "Oi, {name}!\n\n"
            "Eu transformo mensagens de voz em texto. "
            "Envie suas mensagens de voz em qualquer idioma.\n\n"
            "Você pode ativar a tradução automática em /settings.\n\n"
            "Eu não gravo nem guardo nada.)"
        ),
        "settings": (
            "Traduzir as transcrições para o idioma do seu Telegram ({lang}) "
            "quando a mensagem de voz estiver em outro idioma?"
        ),
        "translate_on": "Traduzir",
        "translate_off": "Não traduzir",
        "translate_enabled": "Tradução ativada",
        "translate_disabled": "Tradução desativada",
        "translate_button": "Traduzir",
        "translation_header": "🌐 Tradução ({lang}):",
        "no_speech": "Não foi possível reconhecer nenhuma fala.",
        "transcription_failed": "Não foi possível transcrever, tente novamente.",
        "translation_failed": "Não foi possível traduzir",
        "cmd_start": "Iniciar",
        "cmd_settings": "Configurações de tradução",
    },
    "pl": {
        "start": (
            "Cześć, {name}!\n\n"
            "Zamieniam wiadomości głosowe na tekst. "
            "Wysyłaj mi swoje wiadomości głosowe w dowolnym języku.\n\n"
            "W /settings możesz włączyć automatyczne tłumaczenie.\n\n"
            "Nie nagrywam ani nie przechowuję niczego.)"
        ),
        "settings": (
            "Tłumaczyć transkrypcje na język twojego Telegrama ({lang}), "
            "gdy wiadomość głosowa jest w innym języku?"
        ),
        "translate_on": "Tłumacz",
        "translate_off": "Nie tłumacz",
        "translate_enabled": "Tłumaczenie włączone",
        "translate_disabled": "Tłumaczenie wyłączone",
        "translate_button": "Przetłumacz",
        "translation_header": "🌐 Tłumaczenie ({lang}):",
        "no_speech": "Nie udało się rozpoznać mowy.",
        "transcription_failed": "Nie udało się rozpoznać, spróbuj jeszcze raz.",
        "translation_failed": "Nie udało się przetłumaczyć",
        "cmd_start": "Start",
        "cmd_settings": "Ustawienia tłumaczenia",
    },
    "tr": {
        "start": (
            "Merhaba, {name}!\n\n"
            "Sesli mesajları metne çeviririm. "
            "Bana istediğin dilde sesli mesaj gönder.\n\n"
            "Otomatik çeviriyi /settings içinden açabilirsin.\n\n"
            "Hiçbir şey kaydetmiyor ve saklamıyorum.)"
        ),
        "settings": (
            "Sesli mesaj başka bir dildeyse, metinleri Telegram dilin olan "
            "({lang}) dile çevireyim mi?"
        ),
        "translate_on": "Çevir",
        "translate_off": "Çevirme",
        "translate_enabled": "Çeviri açık",
        "translate_disabled": "Çeviri kapalı",
        "translate_button": "Çevir",
        "translation_header": "🌐 Çeviri ({lang}):",
        "no_speech": "Konuşma algılanamadı.",
        "transcription_failed": "Metne çevrilemedi, tekrar dene.",
        "translation_failed": "Çevrilemedi",
        "cmd_start": "Başlat",
        "cmd_settings": "Çeviri ayarları",
    },
    "ar": {
        "start": (
            "مرحباً، {name}!\n\n"
            "أنا بوت يحوّل الرسائل الصوتية إلى نص. "
            "أرسل لي رسائلك الصوتية بأي لغة.\n\n"
            "يمكنك تفعيل الترجمة التلقائية من خلال /settings.\n\n"
            "لا أسجّل ولا أحتفظ بأي شيء.)"
        ),
        "settings": (
            "هل تريد ترجمة النصوص المفرّغة إلى لغة تيليجرام لديك ({lang}) "
            "عندما تكون الرسالة الصوتية بلغة أخرى؟"
        ),
        "translate_on": "ترجم",
        "translate_off": "عدم الترجمة",
        "translate_enabled": "الترجمة مفعّلة",
        "translate_disabled": "الترجمة معطّلة",
        "translate_button": "ترجم",
        "translation_header": "🌐 الترجمة ({lang}):",
        "no_speech": "تعذّر التعرّف على أي كلام.",
        "transcription_failed": "تعذّر التفريغ، حاول مرة أخرى.",
        "translation_failed": "تعذّرت الترجمة",
        "cmd_start": "ابدأ",
        "cmd_settings": "إعدادات الترجمة",
    },
    "zh": {
        "start": (
            "你好，{name}！\n\n"
            "我可以把语音消息转换成文字。"
            "请发送任何语言的语音消息给我。\n\n"
            "你可以在 /settings 中开启自动翻译。\n\n"
            "我不会录制或保存任何内容。)"
        ),
        "settings": (
            "当语音消息是其他语言时，是否将转写结果翻译成你的 Telegram 语言（{lang}）？"
        ),
        "translate_on": "翻译",
        "translate_off": "不翻译",
        "translate_enabled": "翻译已开启",
        "translate_disabled": "翻译已关闭",
        "translate_button": "翻译",
        "translation_header": "🌐 翻译（{lang}）：",
        "no_speech": "未识别到语音。",
        "transcription_failed": "无法识别，请再试一次。",
        "translation_failed": "无法翻译",
        "cmd_start": "开始",
        "cmd_settings": "翻译设置",
    },
}


def base_language(code: str | None) -> str:
    if not code:
        return DEFAULT_LANGUAGE
    return code.replace("_", "-").split("-")[0].lower()


def ui_language(code: str | None) -> str:
    lang = base_language(code)
    return lang if lang in TEXTS else DEFAULT_LANGUAGE


def t(code: str | None, key: str, **kwargs) -> str:
    return TEXTS[ui_language(code)][key].format(**kwargs)

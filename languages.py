import re

import langcodes

from i18n import ui_language

# Target languages of AssemblyAI translation, from
# https://www.assemblyai.com/docs/speech-understanding/translation
# (regional English variants collapsed into "en").
SUPPORTED_TRANSLATION_LANGUAGES = frozenset(
    "en es fr de it pt nl hi ja zh fi ko pl ru tr uk vi af sq am ar hy as az eu be bn "
    "bs bg ca hr cs da et gl ka el gu ht ha haw he hu is id jw kn kk lo la lv lt lb mk "
    "mg ms ml mt mi mr mn ne no pa ps fa ro sr sn sd si sk sl so su sw sv tl tg ta te "
    "ur uz cy yi yo".split()
)

# AssemblyAI uses the legacy code for Javanese.
_ASSEMBLYAI_CODES = {"jv": "jw"}

_TRAILING_PUNCTUATION = re.compile(r"[\s.,!?;:…。！？]+$")


def resolve_language(text: str) -> str | None:
    text = _TRAILING_PUNCTUATION.sub("", text.strip())
    if not text:
        return None
    try:
        if langcodes.tag_is_valid(text):
            language = langcodes.Language.get(text).language
        else:
            language = langcodes.find(text).language
    except LookupError:
        return None
    if not language:
        return None
    language = _ASSEMBLYAI_CODES.get(language, language)
    return language if language in SUPPORTED_TRANSLATION_LANGUAGES else None


def language_name(code: str, ui_code: str | None) -> str:
    try:
        return langcodes.Language.get(code).display_name(ui_language(ui_code))
    except (LookupError, ValueError):
        return code

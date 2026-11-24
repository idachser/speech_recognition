import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_user(language_code="ru"):
    return SimpleNamespace(first_name="Alex", language_code=language_code)


def make_message(text=None, reply_markup=None):
    return SimpleNamespace(
        chat_id=42,
        text=text,
        reply_markup=reply_markup,
        voice=SimpleNamespace(file_id="voice-id"),
        audio=None,
        reply_text=AsyncMock(),
    )


def make_transcript(
    text="hello",
    language_code="en",
    translated_texts=None,
    transcript_id="t-1",
):
    return SimpleNamespace(
        text=text,
        language_code=language_code,
        translated_texts=translated_texts,
        id=transcript_id,
    )


@pytest.fixture
def context():
    bot = SimpleNamespace(
        get_file=AsyncMock(return_value=SimpleNamespace(file_path="https://file")),
        send_chat_action=AsyncMock(),
    )
    return SimpleNamespace(user_data={}, bot=bot)

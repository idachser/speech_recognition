import pytest

import languages


@pytest.mark.parametrize(
    "text, expected",
    [
        ("немецкий", "de"),
        ("Немецкий", "de"),
        ("Deutsch", "de"),
        ("German", "de"),
        ("alemán", "de"),
        ("de", "de"),
        ("DE.", "de"),
        ("  de!  ", "de"),
        ("pt-BR", "pt"),
        ("Español", "es"),
        ("испанский", "es"),
        ("日本語", "ja"),
        ("javanese", "jw"),
    ],
)
def test_resolve_language(text, expected):
    assert languages.resolve_language(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "...", "klingon", "hello", "xx", "und"])
def test_resolve_language_unknown(text):
    assert languages.resolve_language(text) is None


def test_resolve_language_unsupported_by_assemblyai(monkeypatch):
    monkeypatch.setattr(languages, "SUPPORTED_TRANSLATION_LANGUAGES", frozenset({"en"}))
    assert languages.resolve_language("Deutsch") is None
    assert languages.resolve_language("English") == "en"


@pytest.mark.parametrize(
    "code, ui, expected",
    [
        ("de", "ru", "немецкий"),
        ("de", "en", "German"),
        ("de", "en-GB", "German"),
        ("de", None, "German"),
        ("de", "ja", "German"),
        ("es", "de", "Spanisch"),
        ("zz-@", "en", "zz-@"),
    ],
)
def test_language_name(code, ui, expected):
    assert languages.language_name(code, ui) == expected

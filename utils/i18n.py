"""
i18n - Lightweight UI localization (Phase 1)

A tiny, dependency-free localization layer for the app's user-facing UI strings.

How it works:
- A central ``TRANSLATIONS`` catalog maps a stable string ID (e.g. ``"tab.summarizer"``)
  to its text in each supported language.
- ``t(key)`` returns the string for the currently active language, falling back to
  English (and finally to the key itself) so a missing/partial translation never crashes.
- The active language is chosen in Settings and persisted to ``.env`` (``APP_LANGUAGE``).
  It is loaded once at startup and applied to widgets as they are constructed
  (restart-to-apply: changing the language takes effect on the next launch).

Phase 1 scope: tab titles, header controls, and the Settings dialog chrome.
Additional strings can be localized incrementally by adding keys here and
replacing hardcoded literals with ``t("some.key")`` at the call site.

Created: 2026-08-31
"""

from utils.logger import logger

# --- Supported languages -------------------------------------------------

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "hr")

# Human-readable names shown in the Settings language dropdown.
LANGUAGE_NAMES = {
    "en": "English",
    "hr": "Hrvatski",
}

# --- Translation catalog -------------------------------------------------
# key -> {language_code: text}
# Keep English ("en") authoritative; every key MUST have an "en" value so the
# fallback is always meaningful.
TRANSLATIONS = {
    # Tab titles (leading emoji is part of the label and kept in every language)
    "tab.summarizer":        {"en": "📝 Summarizer",       "hr": "📝 Sažimač"},
    "tab.transcriber":       {"en": "🗡 Transcriber",       "hr": "🗡 Transkriptor"},
    "tab.bulk_summarizer":   {"en": "📦 Bulk Summarizer",   "hr": "📦 Skupno sažimanje"},
    "tab.bulk_transcriber":  {"en": "🎬 Bulk Transcriber",  "hr": "🎬 Skupno transkribiranje"},
    "tab.translation":       {"en": "🌐 Translation",       "hr": "🌐 Prijevod"},
    "tab.downloader":        {"en": "📥 Downloader",        "hr": "📥 Preuzimanje"},
    "tab.video_subtitler":   {"en": "🎞 Video Subtitler",   "hr": "🎞 Titlovanje videa"},

    # Header controls
    "header.font":           {"en": "Font:",               "hr": "Font:"},
    "header.px":             {"en": "px",                  "hr": "px"},
    "header.dark_mode":      {"en": "🌙 Dark Mode",         "hr": "🌙 Tamni način"},
    "header.light_mode":     {"en": "☀️ Light Mode",        "hr": "☀️ Svijetli način"},
    "header.settings":       {"en": "⚙ Settings",          "hr": "⚙ Postavke"},

    # Status bar
    "status.ready":          {"en": "Ready",               "hr": "Spremno"},

    # Settings dialog
    "settings.title":            {"en": "⚙ Settings",       "hr": "⚙ Postavke"},
    "settings.heading":          {"en": "Settings",          "hr": "Postavke"},
    "settings.appearance":       {"en": "Appearance",        "hr": "Izgled"},
    "settings.language":         {"en": "Language:",         "hr": "Jezik:"},
    "settings.language_hint":    {
        "en": "  Applies after you restart the app.",
        "hr": "  Primjenjuje se nakon ponovnog pokretanja aplikacije.",
    },
    "settings.apply_close":      {"en": "Apply & Close",     "hr": "Primijeni i zatvori"},
    "settings.apply":            {"en": "Apply",             "hr": "Primijeni"},
    "settings.cancel":           {"en": "Cancel",            "hr": "Odustani"},
    "settings.restart_title":    {"en": "Restart required",  "hr": "Potrebno ponovno pokretanje"},
    "settings.restart_message":  {
        "en": "The language change will take effect after you restart the application.",
        "hr": "Promjena jezika primijenit će se nakon ponovnog pokretanja aplikacije.",
    },
}

# --- Active language state ------------------------------------------------

_current_language = DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    """Set the active UI language.

    Unknown codes fall back to :data:`DEFAULT_LANGUAGE` so the app never ends up
    in an unrenderable state.

    Args:
        language: A language code from :data:`SUPPORTED_LANGUAGES` (e.g. ``"hr"``).
    """
    global _current_language
    if language in SUPPORTED_LANGUAGES:
        _current_language = language
        logger.info(f"[i18n] Active language set to '{language}'")
    else:
        logger.warning(
            f"[i18n] Unsupported language '{language}', falling back to '{DEFAULT_LANGUAGE}'"
        )
        _current_language = DEFAULT_LANGUAGE


def get_language() -> str:
    """Return the currently active language code."""
    return _current_language


def t(key: str) -> str:
    """Translate a string ID to the active language.

    Falls back to English, then to the raw key, if a translation is missing so
    a partial catalog degrades gracefully instead of raising.

    Args:
        key: A catalog key such as ``"tab.summarizer"``.

    Returns:
        The localized string.
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        logger.warning(f"[i18n] Missing translation key: '{key}'")
        return key
    return entry.get(_current_language) or entry.get(DEFAULT_LANGUAGE) or key


def code_for_name(name: str) -> str:
    """Map a display name (e.g. ``"Hrvatski"``) back to its language code.

    Unknown names fall back to :data:`DEFAULT_LANGUAGE`.
    """
    for code, display in LANGUAGE_NAMES.items():
        if display == name:
            return code
    return DEFAULT_LANGUAGE


def name_for_code(code: str) -> str:
    """Map a language code to its display name (e.g. ``"en"`` -> ``"English"``)."""
    return LANGUAGE_NAMES.get(code, LANGUAGE_NAMES[DEFAULT_LANGUAGE])

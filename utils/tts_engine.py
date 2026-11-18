"""
TTS facade — routes "Read in Voice" to the selected provider.

Providers:
- ``tinyvoca`` (default): local neural model (English, F2/M2 voices).
- ``system``: the OS voice via pyttsx3/SAPI5.

The facade keeps the same public API the rest of the app has always used
(``speak``, ``stop``, ``is_available``, ``is_speaking``, ``get_available_voices``),
so callers are unaffected. Provider selection is read from the environment
(``TTS_PROVIDER``), which is populated from ``.env`` at startup and re-synced
when the Settings dialog applies changes.
"""

import os

from utils import tts_engine_pyttsx3, tts_engine_tinyvoca

# Provider ids.
PROVIDER_TINYVOCA = "tinyvoca"
PROVIDER_SYSTEM = "system"
DEFAULT_PROVIDER = PROVIDER_TINYVOCA


def _env(key, default):
    value = os.environ.get(key, "")
    return value.strip() if value.strip() else default


def _float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_provider() -> str:
    """Return the active provider id ('tinyvoca' or 'system')."""
    provider = _env("TTS_PROVIDER", DEFAULT_PROVIDER).lower()
    return provider if provider in (PROVIDER_TINYVOCA, PROVIDER_SYSTEM) else DEFAULT_PROVIDER


def speak(text):
    """Speak ``text`` using the selected provider (falling back to the system voice)."""
    if not text or not text.strip():
        return

    provider = get_provider()

    if provider == PROVIDER_TINYVOCA:
        if tts_engine_tinyvoca.is_available():
            tts_engine_tinyvoca.speak(
                text,
                voice=_env("TTS_VOICE", "F2"),
                speed=_float(_env("TTS_SPEED", "1.0"), 1.0),
            )
            return
        # Model not ready yet: start a background download so it is available
        # next time, and speak now with the system voice.
        tts_engine_tinyvoca.prepare_async()

    tts_engine_pyttsx3.speak(text)


def stop():
    """Stop whichever provider is currently speaking (both are idempotent)."""
    tts_engine_tinyvoca.stop()
    tts_engine_pyttsx3.stop()


def is_available() -> bool:
    return tts_engine_tinyvoca.is_available() or tts_engine_pyttsx3.is_available()


def is_speaking() -> bool:
    return tts_engine_tinyvoca.is_speaking() or tts_engine_pyttsx3.is_speaking()


def get_available_voices(provider=None):
    """Return the voice list for ``provider`` (defaults to the active provider)."""
    provider = provider or get_provider()
    if provider == PROVIDER_TINYVOCA:
        return tts_engine_tinyvoca.get_voices()
    return tts_engine_pyttsx3.get_available_voices()

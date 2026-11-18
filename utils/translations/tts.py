"""UI strings for the text-to-speech (TTS) settings section.

Keys are namespaced ``settings.speech.*``. Used by views/main_window.py.
"""

STRINGS = {
    "settings.speech": {
        "en": "Speech",
        "hr": "Govor",
    },
    "settings.speech.provider": {
        "en": "Voice provider:",
        "hr": "Davatelj glasa:",
    },
    "settings.speech.provider_tinyvoca": {
        "en": "TinyVoca (local, English)",
        "hr": "TinyVoca (lokalno, engleski)",
    },
    "settings.speech.provider_system": {
        "en": "System voice",
        "hr": "Sistemski glas",
    },
    "settings.speech.voice": {
        "en": "Voice:",
        "hr": "Glas:",
    },
    "settings.speech.speed": {
        "en": "Speed:",
        "hr": "Brzina:",
    },
    "settings.speech.download": {
        "en": "Download TinyVoca model",
        "hr": "Preuzmi TinyVoca model",
    },
    "settings.speech.hint": {
        "en": "  TinyVoca is a small, fully offline English voice. If the model is "
              "not ready, the app falls back to the system voice automatically.",
        "hr": "  TinyVoca je mali, potpuno izvanmrežni engleski glas. Ako model "
              "nije spreman, aplikacija se automatski vraća na sistemski glas.",
    },
}

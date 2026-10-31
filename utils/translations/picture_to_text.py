"""
Picture to Text (OCR) tab UI strings.

Used by views/picture_to_text_tab.py. The emoji tab title itself lives in
common.py under "tab.picture_to_text".

Every key MUST have an "en" value; "hr" is the Croatian translation. Missing
translations fall back to English (see utils.i18n.t).
"""

STRINGS = {
    # Tab title (used in the view header, without the leading tab emoji)
    "picture_to_text.title": {"en": "Picture to text", "hr": "Slika u tekst"},

    # Image picker
    "picture_to_text.frame.image": {"en": "Image", "hr": "Slika"},
    "picture_to_text.btn.browse":  {"en": "📁 Choose image", "hr": "📁 Odaberi sliku"},
    "picture_to_text.no_image":    {"en": "No image selected", "hr": "Nijedna slika nije odabrana"},
    "picture_to_text.dialog.select_image": {"en": "Select an image", "hr": "Odaberite sliku"},
    "picture_to_text.preview.empty":  {"en": "Image preview", "hr": "Pregled slike"},
    "picture_to_text.preview.failed": {"en": "Preview unavailable", "hr": "Pregled nije dostupan"},

    # LLM / provider settings
    "picture_to_text.lbl.provider": {"en": "Server", "hr": "Poslužitelj"},
    "picture_to_text.lbl.base_url": {"en": "Base URL:", "hr": "Osnovni URL:"},
    "picture_to_text.btn.test":     {"en": "Test", "hr": "Testiraj"},
    "picture_to_text.lbl.model":    {"en": "Model:", "hr": "Model:"},
    "picture_to_text.lbl.model_hint": {
        "en": "Pick a vision-capable model (one that accepts images). "
              "Text-only models will fail or return nothing.",
        "hr": "Odaberite model koji podržava slike (vision). "
              "Modeli samo za tekst neće raditi ili neće vratiti ništa.",
    },

    # Connection status
    "picture_to_text.status.need_provider": {"en": "Select a server and URL", "hr": "Odaberite poslužitelj i URL"},
    "picture_to_text.status.connecting":    {"en": "Connecting…", "hr": "Povezivanje…"},
    "picture_to_text.status.connected":     {"en": "Connected", "hr": "Povezano"},
    "picture_to_text.status.unreachable":   {"en": "Server unreachable", "hr": "Poslužitelj nedostupan"},

    # Prompt
    "picture_to_text.lbl.prompt": {"en": "Instruction prompt", "hr": "Uputa modelu"},
    "picture_to_text.prompt.default": {
        "en": "Extract all text visible in the image exactly as it appears, "
              "preserving line breaks and reading order. Return only the "
              "extracted text with no commentary.",
        "hr": "Izvuci sav tekst vidljiv na slici točno onako kako se pojavljuje, "
              "zadržavajući prijelome redaka i redoslijed čitanja. Vrati samo "
              "izvučeni tekst bez komentara.",
    },

    # Output + actions
    "picture_to_text.frame.output": {"en": "Extracted text", "hr": "Izvučeni tekst"},
    "picture_to_text.btn.extract":  {"en": "🔎 Extract text", "hr": "🔎 Izvuci tekst"},
}

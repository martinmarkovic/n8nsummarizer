"""UI strings for the Translation tab (views/translation_tab.py).

Keys are namespaced ``translation.*``. Every key MUST have an "en" value; add
the Croatian "hr" translation alongside it.

Note: the target-language dropdown values ("Croatian", "Deutsch") are NOT
translated here — they are semantic inputs passed to the translation model,
not display-only chrome, so changing them would change behavior.
"""

STRINGS = {
    # Buttons
    "translation.btn.browse":       {"en": "[Browse file...]",  "hr": "[Pregledaj datoteku...]"},
    "translation.btn.translate":    {"en": "Translate",         "hr": "Prevedi"},
    "translation.btn.test":         {"en": "Test",              "hr": "Testiraj"},

    # Labels
    "translation.lbl.translate_to": {"en": "Translate to:",     "hr": "Prevedi na:"},
    "translation.lbl.provider":     {"en": "Provider:",         "hr": "Davatelj:"},
    "translation.lbl.base_url":     {"en": "Base URL:",         "hr": "Osnovni URL:"},
    "translation.lbl.model":        {"en": "Model:",            "hr": "Model:"},
    "translation.chk.remember":     {"en": "Remember settings", "hr": "Zapamti postavke"},

    # Panes
    "translation.frame.source":      {"en": "Source",       "hr": "Izvor"},
    "translation.frame.translation": {"en": "Translation",  "hr": "Prijevod"},

    # Connection / model-discovery status
    "translation.status.need_provider": {"en": "Error: Provider and URL required", "hr": "Greška: potrebni su davatelj i URL"},
    "translation.status.connecting":    {"en": "Connecting...",       "hr": "Povezivanje..."},
    "translation.status.connected":     {"en": "Connected",           "hr": "Povezano"},
    "translation.status.unreachable":   {"en": "Cannot reach server", "hr": "Poslužitelj nije dostupan"},

    # Context-menu items
    "translation.menu.export_txt":  {"en": "Export as .txt",         "hr": "Izvezi kao .txt"},
    "translation.menu.export_srt":  {"en": "Export as .srt",         "hr": "Izvezi kao .srt"},
    "translation.menu.forward":     {"en": "Forward to Summarization", "hr": "Proslijedi na sažimanje"},

    # File-path placeholder (display only)
    "translation.no_file": {"en": "[No file selected]", "hr": "[Nije odabrana datoteka]"},

    # File-open / save dialog titles
    "translation.dialog.select_file": {"en": "Select file to translate", "hr": "Odaberite datoteku za prijevod"},
    "translation.dialog.export_txt":  {"en": "Export Translation",       "hr": "Izvoz prijevoda"},
    "translation.dialog.export_srt":  {"en": "Export SRT Translation",   "hr": "Izvoz SRT prijevoda"},

    # File-type filter labels
    "translation.filetype.text": {"en": "Text files",       "hr": "Tekstualne datoteke"},
    "translation.filetype.all":  {"en": "All files",        "hr": "Sve datoteke"},
    "translation.filetype.srt":  {"en": "SubRip subtitles", "hr": "SubRip titlovi"},

    # Message boxes (titles + bodies). {n}/{path} are filled with str.format().
    "translation.msg.nothing_export_title": {"en": "Nothing to export",       "hr": "Nema ništa za izvoz"},
    "translation.msg.empty_body":           {"en": "Translated text is empty.", "hr": "Prevedeni tekst je prazan."},
    "translation.msg.exported_title":       {"en": "Exported",                "hr": "Izvezeno"},
    "translation.msg.saved_txt":            {"en": "Translation saved to:\n{path}",     "hr": "Prijevod spremljen u:\n{path}"},
    "translation.msg.saved_srt":            {"en": "SRT translation saved to:\n{path}", "hr": "SRT prijevod spremljen u:\n{path}"},
    "translation.msg.export_failed_title":  {"en": "Export Failed",           "hr": "Izvoz nije uspio"},
    "translation.msg.nothing_forward_title":{"en": "Nothing to forward",      "hr": "Nema ništa za proslijediti"},
    "translation.msg.forwarded_title":      {"en": "Forwarded Successfully",  "hr": "Uspješno proslijeđeno"},
    "translation.msg.forwarded_body":       {
        "en": "Translation forwarded to summarization tab ({n} characters)",
        "hr": "Prijevod proslijeđen na karticu sažimanja ({n} znakova)",
    },
    "translation.msg.ready_forward_title":  {"en": "Ready to Forward",        "hr": "Spremno za prosljeđivanje"},
    "translation.msg.ready_forward_body":   {
        "en": "Text is ready. Use the 'Paste Forwarded Text' function in the summarization tab.",
        "hr": "Tekst je spreman. Upotrijebite funkciju 'Zalijepi proslijeđeni tekst' na kartici sažimanja.",
    },
    "translation.msg.forward_confirm_title": {"en": "Forward to Summarization", "hr": "Proslijedi na sažimanje"},
    "translation.msg.forward_confirm_body":  {
        "en": "Forward {n} characters to summarization tab?",
        "hr": "Proslijediti {n} znakova na karticu sažimanja?",
    },
}

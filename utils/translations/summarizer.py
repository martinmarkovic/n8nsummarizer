"""UI strings for the Summarizer tab (views/summarizer_tab.py).

Keys are namespaced ``summarizer.*``. Every key MUST have an "en" value; add
the Croatian "hr" translation alongside it.

Notes on intentionally-untranslated strings (left as literals in the view):
- Provider radio labels ("LM Studio", "Ollama Local") are brand/provider names,
  kept as-is to match the Translation tab.
- "URL:" is a tech token with no surrounding words.
- Export buttons "📄 .txt" / "📝 .docx" are emoji + file-extension only.
- The "●" status dot and "🗑" delete button are symbol-only.
- "No file selected" is NOT localized here: it doubles as a control-flow
  sentinel in ``get_file_path()`` (``path != "No file selected"``), so
  translating it would change behavior.
- {n}/{name}/{path} etc. are filled with str.format(); keep names identical
  across "en" and "hr".
"""

STRINGS = {
    # LabelFrame section titles
    "summarizer.frame.input":           {"en": "Input",                 "hr": "Ulaz"},
    "summarizer.frame.settings":        {"en": "Summarizer Settings",   "hr": "Postavke sažimača"},
    "summarizer.frame.file_info":       {"en": "File Info",             "hr": "Podaci o datoteci"},
    "summarizer.frame.content_preview": {"en": "Content Preview & Edit","hr": "Pregled i uređivanje sadržaja"},
    "summarizer.frame.response":        {"en": "Response",              "hr": "Odgovor"},

    # Input-mode radio buttons (keep leading emoji + spacing)
    "summarizer.radio.file":      {"en": "📄 File",       "hr": "📄 Datoteka"},
    "summarizer.radio.video_url": {"en": "🎬 Video URL",  "hr": "🎬 URL videa"},

    # Input labels / controls
    "summarizer.lbl.file":               {"en": "File:",   "hr": "Datoteka:"},
    "summarizer.btn.browse":             {"en": "Browse…", "hr": "Pregledaj…"},
    "summarizer.lbl.format":             {"en": "Format:", "hr": "Format:"},
    "summarizer.chk.force_retranscribe": {"en": "Force re-transcribe (ignore loaded content)",
                                          "hr": "Prisilno ponovno transkribiraj (zanemari učitani sadržaj)"},

    # Settings labels / controls
    "summarizer.lbl.provider":      {"en": "Provider:",      "hr": "Davatelj:"},
    "summarizer.lbl.base_url":      {"en": "Base URL:",      "hr": "Osnovni URL:"},
    "summarizer.btn.test":          {"en": "Test",           "hr": "Testiraj"},
    "summarizer.chk.remember":      {"en": "Remember settings", "hr": "Zapamti postavke"},
    "summarizer.lbl.model":         {"en": "Model:",         "hr": "Model:"},
    "summarizer.lbl.prompt_preset": {"en": "Prompt Preset:", "hr": "Predložak upita:"},

    # Connection / model-discovery status
    "summarizer.status.need_provider": {"en": "Error: Provider and URL required", "hr": "Greška: potrebni su davatelj i URL"},
    "summarizer.status.connecting":    {"en": "Connecting...",       "hr": "Povezivanje..."},
    "summarizer.status.connected":     {"en": "Connected",           "hr": "Povezano"},
    "summarizer.status.unreachable":   {"en": "Cannot reach server", "hr": "Poslužitelj nije dostupan"},

    # Action bar
    "summarizer.btn.summarize":            {"en": "✨ Summarize",         "hr": "✨ Sažmi"},
    "summarizer.chk.use_original_location":{"en": "Use original location","hr": "Koristi izvornu lokaciju"},
    "summarizer.chk.auto_txt":             {"en": "Auto .txt",           "hr": "Auto .txt"},
    "summarizer.chk.auto_docx":            {"en": "Auto .docx",          "hr": "Auto .docx"},
    "summarizer.lbl.export":               {"en": "Export:",             "hr": "Izvoz:"},
    "summarizer.btn.copy":                 {"en": "📋 Copy",             "hr": "📋 Kopiraj"},
    "summarizer.btn.clear_all":            {"en": "Clear All",           "hr": "Očisti sve"},

    # Prompt-text context menu
    "summarizer.menu.paste":       {"en": "Paste",             "hr": "Zalijepi"},
    "summarizer.menu.copy":        {"en": "Copy",              "hr": "Kopiraj"},
    "summarizer.menu.save_prompt": {"en": "💾 Save as prompt", "hr": "💾 Spremi kao upit"},

    # Preset-combo context menu
    "summarizer.menu.delete_prompt":         {"en": "🗑 Delete prompt",             "hr": "🗑 Izbriši upit"},
    "summarizer.menu.cannot_delete_default": {"en": "Cannot delete default prompt", "hr": "Nije moguće izbrisati zadani upit"},

    # Response context menu
    "summarizer.menu.copy_all":           {"en": "Copy All",                "hr": "Kopiraj sve"},
    "summarizer.menu.clear":              {"en": "Clear",                   "hr": "Očisti"},
    "summarizer.menu.send_to_translation":{"en": "Send to Translation tab", "hr": "Pošalji na karticu prijevoda"},

    # "Save prompt" dialog
    "summarizer.dialog.save_prompt_title": {"en": "Save prompt",   "hr": "Spremi upit"},
    "summarizer.lbl.preset_name":          {"en": "Preset name:",  "hr": "Naziv predloška:"},
    "summarizer.btn.save":                 {"en": "Save",          "hr": "Spremi"},
    "summarizer.btn.cancel":               {"en": "Cancel",        "hr": "Odustani"},

    # Message boxes (titles + bodies)
    "summarizer.msg.empty_prompt_title": {"en": "Empty prompt",              "hr": "Prazan upit"},
    "summarizer.msg.empty_prompt_body":  {"en": "Cannot save an empty prompt.", "hr": "Nije moguće spremiti prazan upit."},
    "summarizer.msg.missing_name_title": {"en": "Missing name",              "hr": "Nedostaje naziv"},
    "summarizer.msg.missing_name_body":  {"en": "Please enter a name.",      "hr": "Unesite naziv."},
    "summarizer.msg.error_title":        {"en": "Error",                     "hr": "Greška"},
    "summarizer.msg.cannot_delete_title":{"en": "Cannot delete",             "hr": "Nije moguće izbrisati"},
    "summarizer.msg.cannot_delete_body": {"en": "Only custom presets (below the separator line) can be deleted.",
                                          "hr": "Mogu se izbrisati samo prilagođeni predlošci (ispod crte razdvajanja)."},
    "summarizer.msg.delete_prompt_title":{"en": "Delete prompt",             "hr": "Izbriši upit"},
    "summarizer.msg.delete_prompt_body": {"en": "Delete custom prompt '{name}'?\nThis cannot be undone.",
                                          "hr": "Izbrisati prilagođeni upit '{name}'?\nOva se radnja ne može poništiti."},
    "summarizer.msg.nothing_send_title": {"en": "Nothing to send",           "hr": "Nema ničega za slanje"},
    "summarizer.msg.nothing_send_body":  {"en": "The response is empty — summarize something first.",
                                          "hr": "Odgovor je prazan — najprije nešto sažmite."},
    "summarizer.msg.unavailable_title":  {"en": "Unavailable",               "hr": "Nedostupno"},
    "summarizer.msg.unavailable_body":   {"en": "The Translation tab isn't available to receive this text.",
                                          "hr": "Kartica prijevoda nije dostupna za primanje ovog teksta."},

    # File-open dialog + file-type filter labels
    "summarizer.dialog.select_file": {"en": "Select file to summarize", "hr": "Odaberite datoteku za sažimanje"},
    "summarizer.filetype.all":       {"en": "All Files",      "hr": "Sve datoteke"},
    "summarizer.filetype.text":      {"en": "Text Files",     "hr": "Tekstualne datoteke"},
    "summarizer.filetype.subtitle":  {"en": "Subtitle Files", "hr": "Datoteke titlova"},
    "summarizer.filetype.json":      {"en": "JSON Files",     "hr": "JSON datoteke"},
    "summarizer.filetype.word":      {"en": "Word Documents", "hr": "Word dokumenti"},

    # Response placeholder + dynamic status strings
    "summarizer.text.get_started":     {"en": "Select a file or enter a YouTube URL and click Summarize to get started…",
                                        "hr": "Odaberite datoteku ili unesite YouTube URL i kliknite Sažmi za početak…"},
    "summarizer.text.response_cleared":{"en": "Response cleared", "hr": "Odgovor je očišćen"},
    "summarizer.status.copied":        {"en": "Copied {n} characters to clipboard",
                                        "hr": "Kopirano {n} znakova u međuspremnik"},
    "summarizer.status.sent_to_translation": {"en": "Sent {n} characters to the Translation tab",
                                              "hr": "Poslano {n} znakova na karticu prijevoda"},
    "summarizer.status.cleared_all":   {"en": "Cleared all", "hr": "Sve očišćeno"},

    # File-info panel (templated; keep the {size:.2f} format spec)
    "summarizer.info.name":    {"en": "Name: {name}",       "hr": "Naziv: {name}"},
    "summarizer.info.size":    {"en": "Size: {size:.2f} KB","hr": "Veličina: {size:.2f} KB"},
    "summarizer.info.lines":   {"en": "Lines: {lines}",     "hr": "Redci: {lines}"},
    "summarizer.info.type":    {"en": "Type: {type}",       "hr": "Vrsta: {type}"},
    "summarizer.info.unknown": {"en": "Unknown",            "hr": "Nepoznato"},

    # File-path placeholder. Displayed AND used as an internal sentinel in
    # get_file_path(); routed through t() consistently so it stays correct under
    # restart-to-apply (language is fixed per session).
    "summarizer.no_file":      {"en": "No file selected",   "hr": "Nije odabrana datoteka"},
}

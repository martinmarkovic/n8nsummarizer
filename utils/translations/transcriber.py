"""UI strings for the Transcriber tab (views/transcriber_tab.py).

Keys are namespaced ``transcriber.*``. Every key MUST have an "en" value; add
the Croatian "hr" translation alongside it.

Note: device labels ("CPU", "CUDA (GPU)", "Insane Mode", "MPS (Mac)"), the
"YouTube URL" radio option, the "URL:" label, and the output-format extensions
(".txt", ".srt", ...) are NOT translated here — they are technical/brand tokens
or semantic inputs paired with logic values, not display-only chrome.
"""

STRINGS = {
    # LabelFrame section titles
    "transcriber.frame.mode":            {"en": "Mode Selection",   "hr": "Odabir načina"},
    "transcriber.frame.input":           {"en": "Input",            "hr": "Ulaz"},
    "transcriber.frame.device":          {"en": "Device",           "hr": "Uređaj"},
    "transcriber.frame.output_location": {"en": "Output Location",  "hr": "Odredište izlaza"},
    "transcriber.frame.output_formats":  {"en": "Output Formats",   "hr": "Izlazni formati"},
    "transcriber.frame.transcript":      {"en": "Transcript (SRT)", "hr": "Transkript (SRT)"},

    # Radiobuttons
    "transcriber.radio.local_file":         {"en": "Local File",         "hr": "Lokalna datoteka"},
    "transcriber.radio.original_location":  {"en": "Original Location",  "hr": "Izvorna lokacija"},
    "transcriber.radio.custom_destination": {"en": "Custom Destination", "hr": "Prilagođeno odredište"},

    # Labels
    "transcriber.lbl.file": {"en": "File:", "hr": "Datoteka:"},
    "transcriber.lbl.path": {"en": "Path:", "hr": "Putanja:"},

    # Buttons
    "transcriber.btn.browse":     {"en": "Browse",               "hr": "Pregledaj"},
    "transcriber.btn.copy":       {"en": "📋 Copy to Clipboard", "hr": "📋 Kopiraj u međuspremnik"},
    "transcriber.btn.export_txt": {"en": "💾 Export .txt",        "hr": "💾 Izvezi .txt"},
    "transcriber.btn.export_srt": {"en": "💾 Export .srt",        "hr": "💾 Izvezi .srt"},
    "transcriber.btn.transcribe": {"en": "🎬 Transcribe",         "hr": "🎬 Transkribiraj"},
    "transcriber.btn.clear":      {"en": "🗑️ Clear",              "hr": "🗑️ Očisti"},

    # Fullscreen context-menu title
    "transcriber.fullscreen.transcript": {"en": "Transcript", "hr": "Transkript"},

    # File-open / folder dialog titles
    "transcriber.dialog.select_media":         {"en": "Select media file",   "hr": "Odaberite medijsku datoteku"},
    "transcriber.dialog.select_output_folder": {"en": "Select output folder", "hr": "Odaberite izlaznu mapu"},

    # File-type filter labels
    "transcriber.filetype.media": {"en": "Media Files", "hr": "Medijske datoteke"},
    "transcriber.filetype.all":   {"en": "All Files",   "hr": "Sve datoteke"},

    # Dynamic status strings
    "transcriber.status.ready":        {"en": "Ready",             "hr": "Spremno"},
    "transcriber.status.transcribing": {"en": "⏳ Transcribing...", "hr": "⏳ Transkribiranje..."},
    "transcriber.status.cleared":      {"en": "Cleared",           "hr": "Očišćeno"},
    "transcriber.status.copied":       {"en": "✓ Copied!",         "hr": "✓ Kopirano!"},

    # Error messages ({error} is filled with str.format()).
    "transcriber.msg.no_transcript_copy": {"en": "No transcript to copy", "hr": "Nema transkripta za kopiranje"},
    "transcriber.msg.copy_failed":        {"en": "Failed to copy: {error}", "hr": "Kopiranje nije uspjelo: {error}"},
}

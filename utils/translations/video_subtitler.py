"""UI strings for the Video Subtitler tab (views/video_subtitler_tab.py).

Keys are namespaced ``video_subtitler.*``. Every key MUST have an "en" value;
add the Croatian "hr" translation alongside it.

Note: several selections are semantic inputs to models/logic rather than
display-only chrome and are therefore NOT translated here:
    - the "Translate to:" language values ("English", "Croatian", ...),
    - the Whisper model / language-code combobox values,
    - the subtitle colour names ("White", "Black", ...) and alignment names
      ("Bottom", "Center", ...), which are used as lookup keys.
Brand/tech tokens (FFmpeg, Whisper, SRT, LLM, URL) are also left as-is.
"""

STRINGS = {
    # LabelFrame section headers
    "video_subtitler.frame.source_settings": {"en": "Video Source Settings", "hr": "Postavke izvora videa"},
    "video_subtitler.frame.progress":        {"en": "Progress",             "hr": "Napredak"},
    "video_subtitler.frame.transcription":   {"en": "Transcription (SRT)",  "hr": "Transkripcija (SRT)"},
    "video_subtitler.frame.translation":     {"en": "Translation",          "hr": "Prijevod"},
    "video_subtitler.frame.burn":            {"en": "Burn Subtitles (FFmpeg)", "hr": "Utisni titlove (FFmpeg)"},
    "video_subtitler.frame.subtitle_style":  {"en": "Subtitle Style",       "hr": "Stil titlova"},

    # Radiobuttons
    "video_subtitler.radio.local_file":     {"en": "Local File",     "hr": "Lokalna datoteka"},
    "video_subtitler.radio.translated_srt": {"en": "Translated SRT", "hr": "Prevedeni SRT"},
    "video_subtitler.radio.original_srt":   {"en": "Original SRT",   "hr": "Izvorni SRT"},

    # Labels
    "video_subtitler.lbl.video_url":          {"en": "Video URL:",         "hr": "URL videa:"},
    "video_subtitler.lbl.local_file":         {"en": "Local File:",        "hr": "Lokalna datoteka:"},
    "video_subtitler.lbl.output_folder":      {"en": "Output folder:",     "hr": "Izlazna mapa:"},
    "video_subtitler.lbl.whisper_model":      {"en": "Whisper Model:",     "hr": "Whisper model:"},
    "video_subtitler.lbl.language":           {"en": "Language:",          "hr": "Jezik:"},
    "video_subtitler.lbl.translate_to":       {"en": "Translate to:",      "hr": "Prevedi na:"},
    "video_subtitler.lbl.subtitle_source":    {"en": "Subtitle source:",   "hr": "Izvor titlova:"},
    "video_subtitler.lbl.background_opacity": {"en": "Background opacity:", "hr": "Neprozirnost pozadine:"},
    "video_subtitler.lbl.font_size":          {"en": "Font size (16 = normal):", "hr": "Veličina fonta (16 = normalno):"},
    "video_subtitler.lbl.text_colour":        {"en": "Text colour:",       "hr": "Boja teksta:"},
    "video_subtitler.lbl.outline_colour":     {"en": "Outline colour:",    "hr": "Boja obruba:"},
    "video_subtitler.lbl.outline_width":      {"en": "Outline width:",     "hr": "Širina obruba:"},
    "video_subtitler.lbl.shadow":             {"en": "Shadow:",            "hr": "Sjena:"},
    "video_subtitler.lbl.position":           {"en": "Position:",          "hr": "Položaj:"},
    "video_subtitler.lbl.vertical_margin":    {"en": "Inset from edge (20 = normal):", "hr": "Razmak od ruba (20 = normalno):"},
    "video_subtitler.lbl.horizontal_scale":   {"en": "Width (100% = normal):", "hr": "Širina (100% = normalno):"},
    "video_subtitler.lbl.vertical_scale":     {"en": "Height (100% = normal):", "hr": "Visina (100% = normalno):"},
    "video_subtitler.lbl.rendering":          {"en": "Subtitle rendering:", "hr": "Prikaz titlova:"},
    "video_subtitler.mode.simple":            {"en": "Simple", "hr": "Jednostavno"},
    "video_subtitler.mode.advanced":          {"en": "Advanced", "hr": "Napredno"},
    "video_subtitler.hint.advanced_style":    {"en": "16 / 100% / 20 are normal subtitle values. Width and height adjust letter shape; keep both at 100% unless needed.", "hr": "16 / 100% / 20 su normalne vrijednosti titlova. Širina i visina mijenjaju oblik slova; zadržite obje na 100% osim ako je potrebno."},

    # Checkbuttons
    "video_subtitler.chk.name_after_original": {"en": "Name output file after original video title", "hr": "Nazovi izlaznu datoteku prema izvornom naslovu videa"},
    "video_subtitler.chk.dark_bg":             {"en": "Darkened background behind subtitles", "hr": "Zatamnjena pozadina iza titlova"},
    "video_subtitler.chk.bold":                {"en": "Bold",   "hr": "Podebljano"},
    "video_subtitler.chk.italic":              {"en": "Italic", "hr": "Kurziv"},

    # Buttons (keep leading emoji + spacing)
    "video_subtitler.btn.browse":              {"en": "Browse",                     "hr": "Pregledaj"},
    "video_subtitler.btn.start":               {"en": "▶ Start",                    "hr": "▶ Pokreni"},
    "video_subtitler.btn.auto":                {"en": "⚡ Auto",                    "hr": "⚡ Automatski"},
    "video_subtitler.btn.change":              {"en": "Change…",                    "hr": "Promijeni…"},
    "video_subtitler.btn.open_temp_folder":    {"en": "📂 Open Temp Folder",        "hr": "📂 Otvori privremenu mapu"},
    "video_subtitler.btn.copy_srt_path":       {"en": "📋 Copy SRT Path",           "hr": "📋 Kopiraj SRT putanju"},
    "video_subtitler.btn.translate_srt":       {"en": "🌐 Translate SRT",           "hr": "🌐 Prevedi SRT"},
    "video_subtitler.btn.save_translated_srt": {"en": "💾 Save Translated SRT",     "hr": "💾 Spremi prevedeni SRT"},
    "video_subtitler.btn.burn":                {"en": "🔥 Burn Subtitles into Video", "hr": "🔥 Utisni titlove u video"},
    "video_subtitler.btn.open_output":         {"en": "📂 Open Output File",        "hr": "📂 Otvori izlaznu datoteku"},

    # Fullscreen context-menu titles
    "video_subtitler.fullscreen.transcription_srt": {"en": "Transcription SRT", "hr": "Transkripcija SRT"},
    "video_subtitler.fullscreen.translated_srt":    {"en": "Translated SRT",    "hr": "Prevedeni SRT"},

    # Dynamic status / info strings shown to the user
    "video_subtitler.status.ready":            {"en": "Ready", "hr": "Spremno"},
    "video_subtitler.status.copied_clipboard": {"en": "Copied to clipboard: {path}", "hr": "Kopirano u međuspremnik: {path}"},
    "video_subtitler.llm.not_configured":      {"en": "Translation LLM: Not configured", "hr": "Prijevodni LLM: nije konfiguriran"},
    "video_subtitler.llm.configured":          {
        "en": "Translation LLM: {provider} / {model} (from Translation tab)",
        "hr": "Prijevodni LLM: {provider} / {model} (s kartice Prijevod)",
    },

    # Message-box titles
    "video_subtitler.msg.info_title":    {"en": "Info",    "hr": "Obavijest"},
    "video_subtitler.msg.error_title":   {"en": "Error",   "hr": "Greška"},
    "video_subtitler.msg.success_title": {"en": "Success", "hr": "Uspjeh"},

    # Message-box bodies ({path}/{error} filled with str.format())
    "video_subtitler.msg.temp_not_exist":        {"en": "Temp folder does not exist yet.", "hr": "Privremena mapa još ne postoji."},
    "video_subtitler.msg.could_not_open_folder": {"en": "Could not open folder: {error}", "hr": "Nije moguće otvoriti mapu: {error}"},
    "video_subtitler.msg.no_translated_to_save": {"en": "No translated SRT content to save.", "hr": "Nema prevedenog SRT sadržaja za spremanje."},
    "video_subtitler.msg.translated_saved":      {"en": "Translated SRT saved to:\n{path}", "hr": "Prevedeni SRT spremljen u:\n{path}"},
    "video_subtitler.msg.failed_save":           {"en": "Failed to save file: {error}", "hr": "Spremanje datoteke nije uspjelo: {error}"},
    "video_subtitler.msg.could_not_open_file":   {"en": "Could not open file: {error}", "hr": "Nije moguće otvoriti datoteku: {error}"},
    "video_subtitler.msg.no_output_file":        {"en": "No output file available yet.", "hr": "Izlazna datoteka još nije dostupna."},

    # File-open / save dialog titles
    "video_subtitler.dialog.select_media":         {"en": "Select video/audio file", "hr": "Odaberite video/audio datoteku"},
    "video_subtitler.dialog.save_translated":      {"en": "Save Translated SRT",     "hr": "Spremi prevedeni SRT"},
    "video_subtitler.dialog.select_output_folder": {"en": "Select output folder",    "hr": "Odaberite izlaznu mapu"},

    # File-type filter labels
    "video_subtitler.filetype.video": {"en": "Video Files", "hr": "Video datoteke"},
    "video_subtitler.filetype.audio": {"en": "Audio Files", "hr": "Audio datoteke"},
    "video_subtitler.filetype.all":   {"en": "All Files",   "hr": "Sve datoteke"},
    "video_subtitler.filetype.srt":   {"en": "SRT Files",   "hr": "SRT datoteke"},
}

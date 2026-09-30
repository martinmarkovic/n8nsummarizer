"""UI strings for the Bulk Transcriber tab.

Covers views/bulk_transcriber_tab.py and views/bulk_transcriber/*.py.
Keys are namespaced ``bulk_transcriber.*``. Every key MUST have an "en" value;
add the Croatian "hr" translation alongside it.

Note: media-format and output-format checkbox labels are keyed by their logic
extension (e.g. ``bulk_transcriber.media.video.mp4``). Only the display label is
translated here; the extension keys themselves are the untouched logic values.
Pure format tokens (MOV, MP3, ...) intentionally have identical en/hr values.
"""

STRINGS = {
    # LabelFrame section titles
    "bulk_transcriber.frame.select_folder":   {"en": "Select Media Folder",        "hr": "Odaberi medijsku mapu"},
    "bulk_transcriber.frame.video":           {"en": "Video Formats",              "hr": "Videoformati"},
    "bulk_transcriber.frame.audio":           {"en": "Audio Formats",              "hr": "Audioformati"},
    "bulk_transcriber.frame.scanning":        {"en": "Scanning Options",           "hr": "Opcije skeniranja"},
    "bulk_transcriber.frame.output_formats":  {"en": "Output Transcript Formats",  "hr": "Formati izlaznog transkripta"},
    "bulk_transcriber.frame.output_location": {"en": "Output Location",            "hr": "Odredište izlaza"},
    "bulk_transcriber.frame.processing":      {"en": "Processing",                 "hr": "Obrada"},
    "bulk_transcriber.frame.progress":        {"en": "Progress",                   "hr": "Napredak"},
    "bulk_transcriber.frame.status_log":      {"en": "Status Log",                 "hr": "Zapisnik statusa"},

    # Buttons
    "bulk_transcriber.btn.browse": {"en": "[Browse...]",         "hr": "[Pregledaj...]"},
    "bulk_transcriber.btn.start":  {"en": "Start Transcribing",  "hr": "Započni transkribiranje"},
    "bulk_transcriber.btn.cancel": {"en": "Cancel",              "hr": "Odustani"},

    # Checkbuttons / Radiobuttons
    "bulk_transcriber.chk.scan_subfolders":  {"en": "Scan Subfolders (recursive scanning)", "hr": "Skeniraj podmape (rekurzivno skeniranje)"},
    "bulk_transcriber.radio.default_location": {"en": "Default (Parent folder of source)",  "hr": "Zadano (nadređena mapa izvora)"},
    "bulk_transcriber.radio.custom_location":  {"en": "Custom Location:",                   "hr": "Prilagođeno odredište:"},

    # Static labels / notes
    "bulk_transcriber.lbl.recursive_hint": {
        "en": "When enabled: Scans all subfolders and maintains folder structure in output",
        "hr": "Kada je omogućeno: skenira sve podmape i zadržava strukturu mapa u izlazu",
    },
    "bulk_transcriber.lbl.output_note": {
        "en": "Note: At least one output format must be selected",
        "hr": "Napomena: mora biti odabran barem jedan izlazni format",
    },
    "bulk_transcriber.lbl.ready": {"en": "Ready", "hr": "Spremno"},
    "bulk_transcriber.lbl.idle":  {"en": "Idle",  "hr": "U mirovanju"},

    # Video format checkbox labels (keyed by extension = logic value; do NOT change keys)
    "bulk_transcriber.media.video.mp4":  {"en": "MP4 (Default)", "hr": "MP4 (zadano)"},
    "bulk_transcriber.media.video.mov":  {"en": "MOV",           "hr": "MOV"},
    "bulk_transcriber.media.video.avi":  {"en": "AVI",           "hr": "AVI"},
    "bulk_transcriber.media.video.mkv":  {"en": "MKV",           "hr": "MKV"},
    "bulk_transcriber.media.video.webm": {"en": "WebM",          "hr": "WebM"},

    # Audio format checkbox labels (keyed by extension = logic value; do NOT change keys)
    "bulk_transcriber.media.audio.mp3":  {"en": "MP3",  "hr": "MP3"},
    "bulk_transcriber.media.audio.wav":  {"en": "WAV",  "hr": "WAV"},
    "bulk_transcriber.media.audio.m4a":  {"en": "M4A",  "hr": "M4A"},
    "bulk_transcriber.media.audio.flac": {"en": "FLAC", "hr": "FLAC"},
    "bulk_transcriber.media.audio.aac":  {"en": "AAC",  "hr": "AAC"},
    "bulk_transcriber.media.audio.wma":  {"en": "WMA",  "hr": "WMA"},
    "bulk_transcriber.media.audio.opus": {"en": "OPUS", "hr": "OPUS"},

    # Output transcript format checkbox labels (keyed by extension = logic value)
    "bulk_transcriber.output.srt":  {"en": "SRT (Default - Subtitles)", "hr": "SRT (zadano - titlovi)"},
    "bulk_transcriber.output.txt":  {"en": "TXT (Plain text)",          "hr": "TXT (obični tekst)"},
    "bulk_transcriber.output.vtt":  {"en": "VTT (WebVTT format)",       "hr": "VTT (WebVTT format)"},
    "bulk_transcriber.output.json": {"en": "JSON (Structured data)",    "hr": "JSON (strukturirani podaci)"},

    # Folder placeholders (also used as in-file sentinels; keep the [] brackets)
    "bulk_transcriber.folder.none":           {"en": "[No folder selected]",      "hr": "[Nije odabrana mapa]"},
    "bulk_transcriber.folder.default_parent": {"en": "[Default (Parent folder)]", "hr": "[Zadano (nadređena mapa)]"},
    "bulk_transcriber.folder.default_named":  {"en": "[Default: {name}]",         "hr": "[Zadano: {name}]"},

    # File-open dialog titles
    "bulk_transcriber.dialog.select_source": {"en": "Select folder with media files to transcribe", "hr": "Odaberite mapu s medijskim datotekama za transkribiranje"},
    "bulk_transcriber.dialog.select_output": {"en": "Select output folder for transcripts",         "hr": "Odaberite izlaznu mapu za transkripte"},

    # Progress strings ({current}/{total}/{filename} filled via str.format())
    "bulk_transcriber.progress.files":      {"en": "{current} / {total} files", "hr": "{current} / {total} datoteka"},
    "bulk_transcriber.progress.processing": {"en": "Processing: {filename}",    "hr": "Obrada: {filename}"},

    # Status-log messages ({name}/{count}/{label} filled via str.format())
    "bulk_transcriber.log.folder_selected": {
        "en": "Folder selected: {name} ({count} matching media files)",
        "hr": "Odabrana mapa: {name} ({count} odgovarajućih medijskih datoteka)",
    },
    "bulk_transcriber.log.no_media_found": {
        "en": "No media files found in selected folder",
        "hr": "Nema medijskih datoteka u odabranoj mapi",
    },
    "bulk_transcriber.log.min_one_media": {
        "en": "At least one media format must be selected",
        "hr": "Mora biti odabran barem jedan medijski format",
    },
    "bulk_transcriber.log.scanning_mode": {
        "en": "Scanning mode updated ({label}): {count} matching files",
        "hr": "Način skeniranja ažuriran ({label}): {count} odgovarajućih datoteka",
    },
    "bulk_transcriber.log.with_subfolders":    {"en": "with subfolders",    "hr": "s podmapama"},
    "bulk_transcriber.log.without_subfolders": {"en": "without subfolders", "hr": "bez podmapa"},
    "bulk_transcriber.log.output_folder_set": {
        "en": "Output folder set to: {name}",
        "hr": "Izlazna mapa postavljena na: {name}",
    },
    "bulk_transcriber.log.start_callback_missing": {
        "en": "ERROR: Start callback not registered. Check main.py",
        "hr": "GREŠKA: povratni poziv za pokretanje nije registriran. Provjerite main.py",
    },
}

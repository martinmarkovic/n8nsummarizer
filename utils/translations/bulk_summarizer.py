"""UI strings for the Bulk Summarizer tab.

Covers views/bulk_summarizer_tab.py and views/bulk_summarizer/*.py.
Keys are namespaced ``bulk_summarizer.*``. Every key MUST have an "en" value;
add the Croatian "hr" translation alongside it.

Notes:
- File-type checkbox labels are keyed by their logic key (txt/srt/docx/pdf/opus)
  via ``bulk_summarizer.filetype.*`` so the display text can be localized while
  the underlying logic key stays untouched. Format tokens like "TXT"/"DOCX"/"PDF"
  are intentionally identical across languages.
- Runtime-interpolated strings use named ``{placeholder}`` tokens filled with
  ``str.format()``; placeholder names are identical across "en"/"hr".
"""

STRINGS = {
    # LabelFrame titles / section headers
    "bulk_summarizer.frame.select_source_folder": {"en": "Select Source Folder",     "hr": "Odaberite izvornu mapu"},
    "bulk_summarizer.frame.file_types":           {"en": "File Types to Scan",       "hr": "Vrste datoteka za pretragu"},
    "bulk_summarizer.frame.scanning_options":     {"en": "Scanning Options",         "hr": "Opcije pretraživanja"},
    "bulk_summarizer.frame.output_format":        {"en": "Output Format Options",    "hr": "Opcije izlaznog formata"},
    "bulk_summarizer.frame.llm_settings":         {"en": "LLM Settings (from Summarizer tab)", "hr": "LLM postavke (iz kartice Sažimanje)"},
    "bulk_summarizer.frame.output_location":      {"en": "Output Location",          "hr": "Izlazna lokacija"},
    "bulk_summarizer.frame.processing":           {"en": "Processing",               "hr": "Obrada"},
    "bulk_summarizer.frame.progress":             {"en": "Progress",                 "hr": "Napredak"},
    "bulk_summarizer.frame.status_log":           {"en": "Status Log",               "hr": "Zapisnik statusa"},

    # Buttons
    "bulk_summarizer.btn.browse":           {"en": "[Browse...]",       "hr": "[Pregledaj...]"},
    "bulk_summarizer.btn.refresh_settings": {"en": "Refresh Settings",  "hr": "Osvježi postavke"},
    "bulk_summarizer.btn.start":            {"en": "Start Processing",  "hr": "Pokreni obradu"},
    "bulk_summarizer.btn.cancel":           {"en": "Cancel",            "hr": "Odustani"},

    # Checkbuttons
    "bulk_summarizer.chk.scan_subfolders": {"en": "Scan Subfolders (recursive scanning)", "hr": "Pretraži podmape (rekurzivno pretraživanje)"},
    "bulk_summarizer.chk.separate_files":  {"en": "Separate Files (Uncombined)",          "hr": "Odvojene datoteke (nespojene)"},
    "bulk_summarizer.chk.combined_file":   {"en": "Combined File (Single output)",        "hr": "Spojena datoteka (jedan izlaz)"},

    # Radiobuttons
    "bulk_summarizer.rb.default_location": {"en": "Default (Parent folder of source)", "hr": "Zadano (nadređena mapa izvora)"},
    "bulk_summarizer.rb.custom_location":  {"en": "Custom Location:",                  "hr": "Prilagođena lokacija:"},

    # Hint / note labels
    "bulk_summarizer.lbl.recursive_hint":     {"en": "When enabled: Scans all subfolders and maintains folder structure in output", "hr": "Kada je omogućeno: pretražuje sve podmape i zadržava strukturu mapa u izlazu"},
    "bulk_summarizer.lbl.output_format_note": {"en": "Note: At least one output format must be selected", "hr": "Napomena: mora biti odabran barem jedan izlazni format"},
    "bulk_summarizer.lbl.llm_inherit_note":   {"en": "Note: LLM settings are inherited from the Summarizer tab", "hr": "Napomena: LLM postavke naslijeđene su iz kartice Sažimanje"},

    # Processing status label
    "bulk_summarizer.status.ready": {"en": "Ready", "hr": "Spremno"},

    # File-type checkbox display labels (keyed by logic key; keys stay untranslated)
    "bulk_summarizer.filetype.txt":  {"en": "TXT",                     "hr": "TXT"},
    "bulk_summarizer.filetype.srt":  {"en": "SRT (Subtitles)",         "hr": "SRT (Titlovi)"},
    "bulk_summarizer.filetype.docx": {"en": "DOCX",                    "hr": "DOCX"},
    "bulk_summarizer.filetype.pdf":  {"en": "PDF",                     "hr": "PDF"},
    "bulk_summarizer.filetype.opus": {"en": "OPUS (Audio transcript)", "hr": "OPUS (Audio transkript)"},

    # Folder placeholders (also used as in-file sentinels; keep the [] brackets so
    # get_output_folder()'s `"[" not in output` check keeps working).
    "bulk_summarizer.folder.none":           {"en": "[No folder selected]",      "hr": "[Nije odabrana mapa]"},
    "bulk_summarizer.folder.default_parent": {"en": "[Default (Parent folder)]",  "hr": "[Zadano (nadređena mapa)]"},
    "bulk_summarizer.folder.default_named":  {"en": "[Default: {name}]",          "hr": "[Zadano: {name}]"},

    # File-open dialog titles
    "bulk_summarizer.dialog.select_folder": {"en": "Select folder to summarize",        "hr": "Odaberite mapu za sažimanje"},
    "bulk_summarizer.dialog.select_output": {"en": "Select output folder for summaries", "hr": "Odaberite izlaznu mapu za sažetke"},

    # Progress display (templates filled with str.format())
    "bulk_summarizer.progress.idle":       {"en": "Idle",                  "hr": "Neaktivno"},
    "bulk_summarizer.progress.files":      {"en": "{current} / {total} files", "hr": "{current} / {total} datoteka"},
    "bulk_summarizer.progress.processing": {"en": "Processing: {filename}", "hr": "Obrada: {filename}"},

    # LLM settings info panel (templates use {value})
    "bulk_summarizer.llm.provider_not_connected":  {"en": "Provider: Not connected",  "hr": "Davatelj: Nije povezano"},
    "bulk_summarizer.llm.provider_not_configured": {"en": "Provider: Not configured", "hr": "Davatelj: Nije konfigurirano"},
    "bulk_summarizer.llm.provider":                {"en": "Provider: {value}",        "hr": "Davatelj: {value}"},
    "bulk_summarizer.llm.base_url_not_configured": {"en": "Base URL: Not configured", "hr": "Osnovni URL: Nije konfigurirano"},
    "bulk_summarizer.llm.base_url":                {"en": "Base URL: {value}",        "hr": "Osnovni URL: {value}"},
    "bulk_summarizer.llm.model_not_selected":      {"en": "Model: Not selected",      "hr": "Model: Nije odabran"},
    "bulk_summarizer.llm.model":                   {"en": "Model: {value}",           "hr": "Model: {value}"},
    "bulk_summarizer.llm.prompt_not_selected":     {"en": "Prompt: Not selected",     "hr": "Upit: Nije odabran"},
    "bulk_summarizer.llm.prompt":                  {"en": "Prompt: {value}",          "hr": "Upit: {value}"},

    # Status-log messages (templates filled with str.format())
    "bulk_summarizer.log.folder_selected":       {"en": "Folder selected: {name} ({count} matching files)", "hr": "Odabrana mapa: {name} ({count} odgovarajućih datoteka)"},
    "bulk_summarizer.log.no_matching":           {"en": "No matching files found",                          "hr": "Nije pronađena nijedna odgovarajuća datoteka"},
    "bulk_summarizer.log.min_one_type":          {"en": "At least one file type must be selected",          "hr": "Mora biti odabrana barem jedna vrsta datoteke"},
    "bulk_summarizer.log.file_types_updated":    {"en": "File types updated: {count} matching files",       "hr": "Vrste datoteka ažurirane: {count} odgovarajućih datoteka"},
    "bulk_summarizer.log.scanning_mode_updated": {"en": "Scanning mode updated ({label}): {count} matching files", "hr": "Način pretraživanja ažuriran ({label}): {count} odgovarajućih datoteka"},
    "bulk_summarizer.log.scan_with_subfolders":  {"en": "with subfolders",    "hr": "s podmapama"},
    "bulk_summarizer.log.scan_without_subfolders": {"en": "without subfolders", "hr": "bez podmapa"},
    "bulk_summarizer.log.output_folder_set":     {"en": "Output folder set to: {name}", "hr": "Izlazna mapa postavljena na: {name}"},
}

"""
Common / shared UI strings (tab titles, header controls, status bar, Settings
dialog chrome). These are used by views/main_window.py.

Every key MUST have an "en" value; "hr" is the Croatian translation. Missing
translations fall back to English (see utils.i18n.t).
"""

STRINGS = {
    # Tab titles (leading emoji is part of the label and kept in every language)
    "tab.summarizer":        {"en": "📝 Summarizer",       "hr": "📝 Sažimač"},
    "tab.transcriber":       {"en": "🗡 Transcriber",       "hr": "🗡 Transkriptor"},
    "tab.bulk_summarizer":   {"en": "📦 Bulk Summarizer",   "hr": "📦 Skupno sažimanje"},
    "tab.bulk_transcriber":  {"en": "🎬 Bulk Transcriber",  "hr": "🎬 Skupno transkribiranje"},
    "tab.translation":       {"en": "🌐 Translation",       "hr": "🌐 Prijevod"},
    "tab.downloader":        {"en": "📥 Downloader",        "hr": "📥 Preuzimanje"},
    "tab.video_subtitler":   {"en": "🎞 Video Subtitler",   "hr": "🎞 Titlovanje videa"},
    "tab.picture_to_text":   {"en": "🖼 Picture to text",   "hr": "🖼 Slika u tekst"},

    # Header controls
    "header.font":           {"en": "Font:",               "hr": "Font:"},
    "header.px":             {"en": "px",                  "hr": "px"},
    "header.dark_mode":      {"en": "🌙 Dark Mode",         "hr": "🌙 Tamni način"},
    "header.light_mode":     {"en": "☀️ Light Mode",        "hr": "☀️ Svijetli način"},
    "header.settings":       {"en": "⚙ Settings",          "hr": "⚙ Postavke"},

    # Status bar
    "status.ready":          {"en": "Ready",               "hr": "Spremno"},

    # Shared base-tab status / actions
    "common.cleared":        {"en": "Cleared",             "hr": "Očišćeno"},
    "common.clear":          {"en": "Clear",               "hr": "Očisti"},

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

    # Settings dialog — Appearance (theme colors)
    "settings.theme_colors_hint": {
        "en": "Theme colors  (leave blank to use default light/dark palette):",
        "hr": "Boje teme  (ostavite prazno za zadanu svijetlu/tamnu paletu):",
    },
    "settings.color.background":  {"en": "Background:", "hr": "Pozadina:"},
    "settings.color.text":        {"en": "Text:",       "hr": "Tekst:"},
    "settings.color.accent":      {"en": "Accent:",     "hr": "Naglasak:"},
    "settings.btn.pick":          {"en": "Pick…",       "hr": "Odaberi…"},
    "settings.btn.clear":         {"en": "Clear",       "hr": "Očisti"},
    "settings.color.pick_bg_title":     {"en": "Background color", "hr": "Boja pozadine"},
    "settings.color.pick_text_title":   {"en": "Text color",       "hr": "Boja teksta"},
    "settings.color.pick_accent_title": {"en": "Accent color",     "hr": "Boja naglaska"},
    "settings.accent_hint": {
        "en": "  Accent tints borders, buttons, tabs and section labels.",
        "hr": "  Naglasak boji obrube, gumbe, kartice i naslove odjeljaka.",
    },

    # Settings dialog — background gradient
    "settings.gradient_enable": {
        "en": "Use a background gradient",
        "hr": "Koristi gradijent pozadine",
    },
    "settings.gradient_from":      {"en": "Gradient from:", "hr": "Gradijent od:"},
    "settings.gradient_to":        {"en": "Gradient to:",   "hr": "Gradijent do:"},
    "settings.gradient_pick_from": {"en": "Gradient start colour", "hr": "Početna boja gradijenta"},
    "settings.gradient_pick_to":   {"en": "Gradient end colour",   "hr": "Završna boja gradijenta"},
    "settings.gradient_direction": {"en": "Gradient direction (ends at):", "hr": "Smjer gradijenta (završava na):"},
    "settings.gradient_flow.top_left": {"en": "Flow: bottom-right → top-left", "hr": "Smjer: dolje desno → gore lijevo"},
    "settings.gradient_flow.top": {"en": "Flow: bottom → top", "hr": "Smjer: dolje → gore"},
    "settings.gradient_flow.top_right": {"en": "Flow: bottom-left → top-right", "hr": "Smjer: dolje lijevo → gore desno"},
    "settings.gradient_flow.left": {"en": "Flow: right → left", "hr": "Smjer: desno → lijevo"},
    "settings.gradient_flow.center": {"en": "Radial: center → edges", "hr": "Radijalno: sredina → rubovi"},
    "settings.gradient_flow.right": {"en": "Flow: left → right", "hr": "Smjer: lijevo → desno"},
    "settings.gradient_flow.bottom_left": {"en": "Flow: top-right → bottom-left", "hr": "Smjer: gore desno → dolje lijevo"},
    "settings.gradient_flow.bottom": {"en": "Flow: top → bottom", "hr": "Smjer: gore → dolje"},
    "settings.gradient_flow.bottom_right": {"en": "Flow: top-left → bottom-right", "hr": "Smjer: gore lijevo → dolje desno"},
    "settings.gradient_hint": {
        "en": "  Both colours are required. The gradient fills the tab area; "
              "cards and panels stay solid so text stays readable.",
        "hr": "  Obje boje su obavezne. Gradijent ispunjava područje kartice; "
              "kartice i ploče ostaju pune boje kako bi tekst ostao čitljiv.",
    },

    # Settings dialog — font size
    "settings.font_size":      {"en": "Font size:", "hr": "Veličina fonta:"},
    "settings.font_size_hint": {
        "en": "(currently {size}px — change via the header controls)",
        "hr": "(trenutno {size}px — promijenite putem kontrola u zaglavlju)",
    },

    # Settings dialog — Paths
    "settings.paths":      {"en": "Paths", "hr": "Putanje"},
    "settings.paths_hint": {
        "en": "Paths saved to .env override the built-in defaults.",
        "hr": "Putanje spremljene u .env nadjačavaju ugrađene zadane vrijednosti.",
    },
    "settings.ffmpeg":     {"en": "FFmpeg:", "hr": "FFmpeg:"},
    "settings.btn.browse": {"en": "Browse…", "hr": "Pregledaj…"},
    "settings.ffmpeg_default_hint": {
        "en": "  Default: {path}  (searched on system PATH if blank)",
        "hr": "  Zadano: {path}  (traži se u sistemskom PATH-u ako je prazno)",
    },
    "settings.transcribe_hint": {
        "en": "  (transcribe-anything is a pip package — manage its version in the Dependencies Manager below.)",
        "hr": "  (transcribe-anything je pip paket — upravljajte njegovom verzijom u Upravitelju ovisnosti u nastavku.)",
    },

    # Settings dialog — Tools
    "settings.tools":            {"en": "Tools", "hr": "Alati"},
    "settings.deps_manager_btn": {"en": "⬆  Dependencies Manager…", "hr": "⬆  Upravitelj ovisnosti…"},
    "settings.browse_exe_title": {"en": "Select executable", "hr": "Odaberite izvršnu datoteku"},

    # Dependencies Manager window
    "deps.title":              {"en": "⚙ Dependencies Manager", "hr": "⚙ Upravitelj ovisnosti"},
    "deps.heading":            {"en": "Dependencies Manager",   "hr": "Upravitelj ovisnosti"},
    "deps.installed_versions": {"en": "Installed versions",     "hr": "Instalirane verzije"},
    "deps.btn.update":         {"en": "Update",    "hr": "Ažuriraj"},
    "deps.btn.downgrade":      {"en": "Downgrade",  "hr": "Vrati na stariju"},
    "deps.btn.check":          {"en": "Check",      "hr": "Provjeri"},
    "deps.output":             {"en": "Output",     "hr": "Izlaz"},
    "deps.btn.close":          {"en": "Close",      "hr": "Zatvori"},
    "deps.btn.update_all":     {"en": "⬆ Update All pip packages", "hr": "⬆ Ažuriraj sve pip pakete"},
    "deps.checking":           {"en": "checking…",  "hr": "provjeravam…"},
    "deps.system":             {"en": "(system)",   "hr": "(sustav)"},
}

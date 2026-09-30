"""UI strings for the Downloader tab (views/downloader_tab.py).

Keys are namespaced ``downloader.*``. Every key MUST have an "en" value; add
the Croatian "hr" translation alongside it.

Note: browser identifiers ("chrome", "firefox", ...), quality/resolution
presets ("Best Available", "Audio Only (MP3)", ...) and the visual separator
line are NOT translated here — they are semantic values compared/stored in
logic, not display-only chrome.
"""

STRINGS = {
    # Section frames
    "downloader.frame.settings":    {"en": "Download Settings",  "hr": "Postavke preuzimanja"},
    "downloader.frame.instagram":   {"en": "Instagram Settings", "hr": "Instagram postavke"},
    "downloader.frame.video_info":  {"en": "Video Information",  "hr": "Informacije o videu"},
    "downloader.frame.progress":    {"en": "Download Progress",  "hr": "Napredak preuzimanja"},

    # Labels
    "downloader.lbl.youtube_url":              {"en": "YouTube URL:",             "hr": "YouTube URL:"},
    "downloader.lbl.save_to":                  {"en": "Save to:",                 "hr": "Spremi u:"},
    "downloader.lbl.quality":                  {"en": "Quality:",                 "hr": "Kvaliteta:"},
    "downloader.lbl.po_token":                 {"en": "PO Token:",                "hr": "PO Token:"},
    "downloader.lbl.cookie_file":              {"en": "Cookie File:",             "hr": "Datoteka kolačića:"},
    "downloader.lbl.cookie_browser":           {"en": "Cookie Browser:",          "hr": "Preglednik za kolačiće:"},
    "downloader.lbl.cookie_help":              {"en": "Required for Stories and private content", "hr": "Potrebno za priče i privatni sadržaj"},
    "downloader.lbl.facebook_cookie_file":     {"en": "Facebook Cookie File:",    "hr": "Facebook datoteka kolačića:"},
    "downloader.lbl.facebook_cookie_browser":  {"en": "Facebook Cookie Browser:", "hr": "Facebook preglednik za kolačiće:"},
    "downloader.lbl.facebook_cookie_help":     {"en": "Required for private Facebook videos", "hr": "Potrebno za privatne Facebook videozapise"},

    # Buttons
    "downloader.btn.info":     {"en": "Info",        "hr": "Info"},
    "downloader.btn.browse":   {"en": "Browse...",   "hr": "Pregledaj..."},
    "downloader.btn.download": {"en": "⬇ Download",  "hr": "⬇ Preuzmi"},
    "downloader.btn.help":     {"en": "❓ Help",     "hr": "❓ Pomoć"},

    # Runtime status / progress strings
    "downloader.status.no_folder": {"en": "[No folder selected]", "hr": "[Nije odabrana mapa]"},
    "downloader.status.ready":     {"en": "Ready",                "hr": "Spremno"},

    # Status-log messages ({path}/{resolution}/{browser} filled via str.format()).
    "downloader.log.folder_set":                     {"en": "Download folder set: {path}",              "hr": "Mapa za preuzimanje postavljena: {path}"},
    "downloader.log.quality_changed":                {"en": "Quality changed to: {resolution}",         "hr": "Kvaliteta promijenjena na: {resolution}"},
    "downloader.log.token_updated":                  {"en": "PO Token updated (stored for future use)", "hr": "PO Token ažuriran (spremljen za buduću upotrebu)"},
    "downloader.log.token_cleared":                  {"en": "PO Token cleared",                         "hr": "PO Token obrisan"},
    "downloader.log.instagram_cookie_file_set":      {"en": "Instagram cookie file set: {path}",        "hr": "Instagram datoteka kolačića postavljena: {path}"},
    "downloader.log.instagram_cookie_file_cleared":  {"en": "Instagram cookie file cleared",            "hr": "Instagram datoteka kolačića obrisana"},
    "downloader.log.instagram_cookie_browser_set":   {"en": "Instagram cookie browser set: {browser}",  "hr": "Instagram preglednik za kolačiće postavljen: {browser}"},
    "downloader.log.instagram_cookie_browser_cleared": {"en": "Instagram cookie browser cleared",       "hr": "Instagram preglednik za kolačiće obrisan"},
    "downloader.log.facebook_cookie_file_set":       {"en": "Facebook cookie file set: {path}",         "hr": "Facebook datoteka kolačića postavljena: {path}"},
    "downloader.log.facebook_cookie_file_cleared":   {"en": "Facebook cookie file cleared",             "hr": "Facebook datoteka kolačića obrisana"},
    "downloader.log.facebook_cookie_browser_set":    {"en": "Facebook cookie browser set: {browser}",   "hr": "Facebook preglednik za kolačiće postavljen: {browser}"},
    "downloader.log.facebook_cookie_browser_cleared": {"en": "Facebook cookie browser cleared",         "hr": "Facebook preglednik za kolačiće obrisan"},

    # PO Token help dialog
    "downloader.help.po_token_title": {"en": "PO Token Help", "hr": "Pomoć za PO Token"},
    "downloader.help.po_token_body": {
        "en": (
            "PO Token (optional) can be used for future features.\n\n"
            "Current downloads work without PO Token using simplified format strings.\n\n"
            "How to get PO Token (if needed later):\n\n"
            "1. Install the browser extension (see docs/browser_extension/)\n"
            "2. Open YouTube in your browser\n"
            "3. Click the extension icon\n"
            "4. Click 'Extract PO Token'\n"
            "5. Token is automatically copied to clipboard\n"
            "6. Paste it here\n\n"
            "Token lasts 2-7 days before needing refresh.\n\n"
            "Manual extraction: See docs/YOUTUBE_PO_TOKEN_GUIDE.md"
        ),
        "hr": (
            "PO Token (neobavezno) može se koristiti za buduće značajke.\n\n"
            "Trenutna preuzimanja rade bez PO Tokena koristeći pojednostavljene formatne nizove.\n\n"
            "Kako doći do PO Tokena (ako zatreba kasnije):\n\n"
            "1. Instalirajte proširenje preglednika (pogledajte docs/browser_extension/)\n"
            "2. Otvorite YouTube u pregledniku\n"
            "3. Kliknite ikonu proširenja\n"
            "4. Kliknite 'Extract PO Token'\n"
            "5. Token se automatski kopira u međuspremnik\n"
            "6. Zalijepite ga ovdje\n\n"
            "Token traje 2-7 dana prije nego što ga treba osvježiti.\n\n"
            "Ručno izdvajanje: pogledajte docs/YOUTUBE_PO_TOKEN_GUIDE.md"
        ),
    },

    # File-open / folder-select dialog titles
    "downloader.dialog.select_folder":          {"en": "Select Download Folder",      "hr": "Odaberite mapu za preuzimanje"},
    "downloader.dialog.select_cookie":          {"en": "Select cookie file",          "hr": "Odaberite datoteku kolačića"},
    "downloader.dialog.select_facebook_cookie": {"en": "Select Facebook cookie file", "hr": "Odaberite Facebook datoteku kolačića"},

    # File-type filter labels
    "downloader.filetype.cookie": {"en": "Cookie Files", "hr": "Datoteke kolačića"},
    "downloader.filetype.all":    {"en": "All Files",    "hr": "Sve datoteke"},

    # Message boxes (titles + bodies)
    "downloader.msg.no_url_title":   {"en": "No URL",                          "hr": "Nema URL-a"},
    "downloader.msg.no_url_body":    {"en": "Please enter a YouTube URL first", "hr": "Najprije unesite YouTube URL"},
    "downloader.msg.error_title":    {"en": "Download Error",                  "hr": "Greška pri preuzimanju"},
    "downloader.msg.complete_title": {"en": "Download Complete",               "hr": "Preuzimanje dovršeno"},
}

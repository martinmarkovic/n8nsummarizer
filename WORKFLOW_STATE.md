# Workflow State

## Current Task
First commit on `v13.6.2` (branched from `v13.6.1`): add Copy/Paste context menus
across tabs, Chrome-style tab hotkeys, and a hardened FFmpeg burn.

## Changes Included (staged for commit on v13.6.2)
- `views/context_menu.py`: add `add_copy_command()` / `add_paste_command()` that
  work on both tk.Text and (ttk.)Entry widgets.
- `views/base_tab.py`: `_register_context_menu` supports `copy`/`paste` items; new
  `_register_entry_context_menu(entry, allow_paste)` helper.
- `views/downloader_tab.py`, `views/summarizer_tab.py`, `views/transcriber_tab.py`,
  `views/translation_tab.py`, `views/video_subtitler_tab.py`: attach copy/paste to
  URL/entry/text widgets; status logs get a Copy item; Summarizer prompt right-click
  gets Paste/Copy + Save as prompt.
- `views/bulk_summarizer_tab.py`, `views/bulk_transcriber_tab.py`: status log Copy item.
- `views/main_window.py`: Chrome-style Ctrl+1..Ctrl+8 / Ctrl+9 tab hotkeys
  (`_setup_tab_hotkeys`, `_select_tab_by_index`).
- `controllers/video_subtitler_controller.py`: harden FFmpeg burn — resolve ffmpeg/ffprobe
  (honours FFMPEG_PATH), `-nostdin -hide_banner`, machine-readable `-progress pipe:1`
  parsing on stdout (stderr drained on thread to avoid deadlock), drive-colon escaping,
  clearer errors (executable-not-found, font-cache note, stderr tail).

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged changes.
- Push to new upstream `origin/v13.6.2`.

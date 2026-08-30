# Workflow State

## Current Task
Commit and push current feature work on new branch `v13.5.4` (branched from `v13.5.3`, which was branched from `v13.5.2`).

## Changes Included (staged for commit on v13.5.4)
- `views/fullscreen.py` (new): reusable fullscreen (zoomed) Text viewer with a
  small ⛶ overlay button; optional editable mode writes back to source on close;
  carries TTS read/stop context menu (reads selection if present).
- `views/summarizer_tab.py`: add visible 🗑 delete button for custom presets
  (enabled only when a custom preset is selected); response text is read-only but
  selectable (`_make_readonly_selectable`, `_set_readonly_text`) so TTS can read
  a selection; fullscreen expand on content + response.
- `views/transcriber_tab.py`, `views/translation_tab.py`, `views/video_subtitler_tab.py`:
  attach fullscreen expand buttons to transcript/source/target/SRT text areas.
- `utils/tts_engine_pyttsx3.py`: store active engine in module-level ref and call
  `engine.stop()` from `stop()` for immediate interruption; fix `get_available_voices`
  to use a fresh engine instead of reading the stale module `_engine`.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged feature changes.
- Push to new upstream `origin/v13.5.4`.

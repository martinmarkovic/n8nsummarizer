# Workflow State

## Current Task
Second commit on `v13.5.4` (follow-up to `4ea026e`): move fullscreen/TTS into the
right-click context menu across tabs and improve dark-theme recoloring.

## Changes Included (staged for commit on v13.5.4)
- `views/base_tab.py`: `_register_context_menu` now supports `tts_read`, `tts_stop`,
  `separator`, and `fullscreen` item descriptors; add shared `_selection_or_all`.
- `views/context_menu.py`: add `add_fullscreen_command(...)` helper.
- `views/summarizer_tab.py`: replace ⛶ overlay buttons with consolidated right-click
  context menus (Copy/Clear + TTS + Fullscreen) for content and response.
- `views/transcriber_tab.py`, `views/translation_tab.py`, `views/video_subtitler_tab.py`:
  swap overlay ⛶ buttons for right-click TTS + Fullscreen menu items.
- `views/main_window.py`: dark/light theme now recolors `TCombobox`, `TSpinbox`,
  `Horizontal.TScale`, combobox dropdown list, and every tk.Text/ScrolledText widget
  recursively (`_recolor_text_widgets`).
- `views/fullscreen.py`: inherit the source widget's bg/fg colors.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged follow-up changes.
- Push to existing upstream `origin/v13.5.4`.

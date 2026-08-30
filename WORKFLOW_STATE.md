# Workflow State

## Current Task
First commit on `v13.5.5` (branched from `v13.5.4`): add subtitle style options to
the Video Subtitler burn flow with persisted prefs; improve theme/font ordering.

## Changes Included (staged for commit on v13.5.5)
- `views/video_subtitler_tab.py`: add "Subtitle Style" panel (font size, bold/italic,
  text/outline colour, outline width, shadow, position alignment, vertical margin,
  h/v scale). Exposes `get_subtitle_style()`, `get_burn_prefs()`, `apply_burn_prefs()`.
- `controllers/video_subtitler_controller.py`: burn uses the selected style to build
  `force_style` for ffmpeg subtitles filter (BorderStyle 4 opaque box vs 1 outline+shadow);
  persist/load style prefs to `.env` via SettingsManager (`SUBTITLE_*` keys).
- `views/main_window.py`: define base ('.') style so all ttk widgets inherit theme
  colors; apply theme before font size and re-apply font size after theme toggle so
  user font size isn't reset.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged changes.
- Push to new upstream `origin/v13.5.5`.

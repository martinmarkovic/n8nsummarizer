# Workflow State

## Current Task
First commit on `v13.6` (branched from `v13.5.5`): add a full Settings dialog
(custom theme colors, font entry, path overrides), improve executable path
resolution in cli_runner, and document new .env options.

## Changes Included (staged for commit on v13.6)
- `views/main_window.py`:
  - New "⚙ Settings" popup (replaces direct cogwheel → deps): Appearance (custom
    BG/Text/Accent colors with color-picker + live preview + Clear), font size
    note, Paths (FFmpeg), Tools (Dependencies Manager shortcut).
  - Font size now a direct-entry field clamped to [FONT_MIN=8, FONT_MAX=20];
    +2/-2 buttons and `.env` save via SettingsManager.
  - `_rebuild_theme_colors()` overlays saved custom colors onto base palette;
    `_sync_path_env_vars()` pushes SettingsManager path values into os.environ;
    theme toggle resets custom colors.
  - Dependencies Manager adds `transcribe-anything` pip row.
- `models/transcription/cli_runner.py`: `_resolve_transcribe_path()` /
  `_resolve_ffmpeg_path()` with priority env var → hardcoded default → PATH.
- `.env.example`: document APP_COLOR_BG/TEXT/ACCENT, APP_THEME, APP_FONT_SIZE,
  FFMPEG_PATH, TRANSCRIBE_PATH.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged changes.
- Push to new upstream `origin/v13.6`.
- Then branch out to `v13.6.1`.

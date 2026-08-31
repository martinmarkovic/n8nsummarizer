# Workflow State

## Current Task
First commit on `v13.6.3` (branched from `v13.6.2`): add lightweight UI
localization (i18n) — Phase 1 (tab titles, header, Settings dialog).

## Changes Included (staged for commit on v13.6.3)
- `utils/i18n.py` (new): dependency-free catalog (`t(key)`), supported languages
  `en`/`hr`, active-language state, `code_for_name`/`name_for_code`. Falls back to
  English then the raw key.
- `utils/settings_manager.py`: `get_language()` / `set_language()` (persist to
  `APP_LANGUAGE`).
- `views/main_window.py`: activate saved language before widget build; replace
  hardcoded tab titles, header controls, status "Ready", and Settings-dialog chrome
  with `t(...)`; add a Language dropdown (Appearance section); language change is
  restart-to-apply (shows prompt, returns `language_changed` from
  `_apply_settings_from_dialog`).
- `.env.example`: document `APP_LANGUAGE`.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.
- Scratch `temp_subtitler/*.srt` deletions are gitignored output and NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged changes.
- Push to new upstream `origin/v13.6.3`.
- Then branch out to `v13.6.4`.

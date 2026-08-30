# Workflow State

## Current Task
Commit and push the current working-tree changes on branch `v13.5.2`.

## Changes Included (staged for commit)
- `utils/version.py` (new): derive app version from active git branch (e.g. `v13.5.2`)
  and expose `get_titled_version()`.
- `views/main_window.py`: title now shows `APP_TITLE (vX.Y.Z)` from git branch;
  reworked Dependencies Manager to show installed/available versions with
  Update + Downgrade buttons (uses `importlib.metadata`, `pip index versions`,
  `packaging.parse`).
- `models/translation/service.py`: pass `timeout` through to `LLMClient` so long
  local-model SRT batches don't hit the global 120s `LLM_TIMEOUT`.
- `controllers/video_subtitler_controller.py`: track exact `input_video_path` of
  the just-processed/downloaded video so the burn step uses that file instead of
  a stale `video.*` leftover in the temp folder; deterministic fallback scan.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`v13.5.2`) pushed with the same name.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are already
  tracked historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged source changes.
- Push to new upstream `origin/v13.5.2`.

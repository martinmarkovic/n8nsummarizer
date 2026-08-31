# Workflow State

## Current Task
First commit on `v13.6.1` (branched from `v13.6`): add "Send to Translation tab"
from Summarizer response, and a "Check" (update available) button in the
Dependencies Manager.

## Changes Included (staged for commit on v13.6.1)
- `views/summarizer_tab.py`: add context-menu item "Send to Translation tab" on
  the response text (`_send_to_translation`); new `on_send_to_translation` callback.
- `main.py`: wire `window.summarizer_tab.on_send_to_translation` to set the
  Translation tab's Source box and switch to it.
- `views/main_window.py` (Dependencies Manager): add a "Check" per-row button
  (`_check_update`) that compares installed vs newest available version and logs
  UP TO DATE / UPDATE AVAILABLE / not installed.

## Source of Truth Notes
- `main` is the long-lived branch; feature branches are version-tagged branches
  (`vX.Y.Z`) pushed with the same name, each branched from the previous.
- `.gitignore` covers `__pycache__/*.pyc`, but a few `.pyc` files are tracked
  historically; those binary churn entries are intentionally NOT staged.

## Open Questions
- None.

## Next Steps
- Commit staged changes.
- Push to existing upstream `origin/v13.6.1` (new upstream).

"""
Version utilities.

Derives the application version from the current git branch name.
Branches are named like "v13.5.2", so the branch name doubles as the version.
"""
import subprocess
from pathlib import Path

from utils.logger import logger

# Project root (one level up from this utils/ folder)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_app_version() -> str:
    """
    Return the current version derived from the active git branch.

    Returns the branch name (e.g. "v13.5.2") when it looks like a version tag,
    otherwise returns an empty string. Never raises — falls back to "" on any
    error (git not installed, not a repo, detached HEAD, etc.).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""

        branch = result.stdout.strip()

        # Only treat version-like branches (v1, v13.5.2, ...) as a version
        if branch and branch.lstrip("vV")[:1].isdigit():
            return branch

        return ""
    except Exception as e:
        logger.debug(f"Could not determine app version from git: {e}")
        return ""


def get_titled_version(app_title: str) -> str:
    """
    Return the app title with the version appended in parentheses when available.

    Example: "Media SwissKnife" -> "Media SwissKnife (v13.5.2)"
    Falls back to the plain title if no version can be determined.
    """
    version = get_app_version()
    return f"{app_title} ({version})" if version else app_title

"""Filename sanitisation helpers (Windows/MAX_PATH aware)."""

from __future__ import annotations

import re
from pathlib import Path

from utils.logger import logger


WINDOWS_MAX_PATH = 260
SAFE_FILENAME_MAX = 80


def sanitize_filename(filename: str, output_dir: Path | None = None) -> str:
    """Sanitize filename for Windows filesystem with MAX_PATH compliance.

    Mirrors TranscribeModel._sanitize_filename behaviour.
    """

    forbidden = r"[<>:\"/\\|?*]"
    sanitized = re.sub(forbidden, "_", filename)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.rstrip(". ")

    if output_dir:
        dir_path_len = len(str(output_dir))
        available_for_filename = WINDOWS_MAX_PATH - dir_path_len - 25

        logger.info(
            "Path length budget: total=%s, dir=%s, available=%s",
            WINDOWS_MAX_PATH,
            dir_path_len,
            available_for_filename,
        )

        if available_for_filename < 20:
            logger.warning(
                "Output directory path is very long (%s chars), using minimal filename",
                dir_path_len,
            )
            max_len = 20
        else:
            max_len = min(available_for_filename, 200)
    else:
        max_len = SAFE_FILENAME_MAX

    if len(sanitized) > max_len:
        logger.info("Filename too long (%s > %s), truncating", len(sanitized), max_len)
        sanitized = sanitized[:max_len].rstrip("_")
        logger.info("Truncated to: %s", sanitized)

    return sanitized

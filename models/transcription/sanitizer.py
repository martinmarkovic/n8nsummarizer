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
    Also performs collision detection: if *output_dir* is provided and a file
    with the sanitized name already exists (any known transcript extension),
    appends a numeric suffix (_001, _002, …) until a free name is found.
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

    # ------------------------------------------------------------------
    # Collision detection: ensure the resulting name is unique inside
    # output_dir by appending _001, _002, … when needed.
    # ------------------------------------------------------------------
    if output_dir is not None:
        TRANSCRIPT_EXTENSIONS = (".srt", ".txt", ".vtt", ".json", ".tsv")
        candidate = sanitized
        counter = 1

        def _name_taken(name: str) -> bool:
            """Return True if *any* transcript extension already exists."""
            return any(
                (output_dir / f"{name}{ext}").exists()
                for ext in TRANSCRIPT_EXTENSIONS
            )

        while _name_taken(candidate):
            candidate = f"{sanitized}_{counter:03d}"
            counter += 1
            if counter > 9999:
                logger.error(
                    "Could not find a unique filename for '%s' after 9999 attempts",
                    sanitized,
                )
                break

        if candidate != sanitized:
            logger.info(
                "Filename collision detected – renamed '%s' -> '%s'",
                sanitized,
                candidate,
            )

        sanitized = candidate

    return sanitized

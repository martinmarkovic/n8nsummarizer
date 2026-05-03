"""CLI runner helper for transcribe-anything.

Extracted from models/transcribe_model.py to keep subprocess and
encoding details in a single place.
"""

from __future__ import annotations

import os
import subprocess
import shlex
from typing import Optional, Tuple

from utils.logger import logger


def run_transcribe_cli(
    input_path: str,
    output_dir: str,
    device: str = "cuda",
    timeout_seconds: int = 1800,
) -> Tuple[bool, Optional[str]]:
    """Execute the transcribe-anything CLI command.

    Returns (success, error_message).
    """

    try:
        # Properly quote input_path to handle special characters like &, |, >, <, etc.
        # This prevents shell interpretation issues on Windows
        safe_input_path = shlex.quote(input_path) if os.name == 'nt' else input_path
        
        cmd = [
            "transcribe-anything",
            input_path,  # Use original for list format (safe)
            "--device",
            device,
            "--output_dir",
            output_dir,
        ]
        
        # For logging, use the safe version to avoid shell interpretation in logs
        logger.info("Running: %s … --device %s", " ".join(cmd[:2]), device)
        logger.debug("Full command: %s", " ".join([shlex.quote(arg) if isinstance(arg, str) else str(arg) for arg in cmd]))

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            error_output = result.stderr or result.stdout or ""

            if "UnicodeEncodeError" in error_output or "charmap" in error_output:
                error = (
                    "Unicode filename error: filename contains characters not "
                    "supported by system encoding. Try renaming file to ASCII "
                    "characters only."
                )
                logger.error(
                    "Transcription failed with Unicode error for: %s", input_path
                )
                logger.error("Details: %s", error_output[:200])
                return False, error
            
            # Handle JavaScript runtime issues for YouTube URLs
            if "JavaScript runtime" in error_output or "EJS" in error_output:
                error = (
                    "YouTube extraction requires a JavaScript runtime (Node.js or Deno). "
                    "Please install Node.js or configure yt-dlp with --js-runtimes. "
                    "See: https://github.com/yt-dlp/yt-dlp/wiki/EJS"
                )
                logger.error(
                    "YouTube extraction failed due to missing JavaScript runtime"
                )
                return False, error

            logger.error(
                "Transcription process returned non-zero exit code: %s",
                result.returncode,
            )
            logger.error("STDERR: %s", error_output[:500])
            logger.error(
                "STDOUT: %s",
                result.stdout[:500] if result.stdout else "(empty)",
            )

            display_error = (
                error_output.split("\n")[0] if error_output else "Unknown error"
            )
            return False, f"Transcription failed: {display_error}"

        logger.debug("Transcription succeeded, stdout: %s", result.stdout[:100])
        return True, None

    except subprocess.TimeoutExpired:
        error = "Transcription timeout (30 minutes exceeded)"
        logger.error(error)
        return False, error
    except Exception as exc:  # noqa: BLE001
        error = f"Error running transcribe-anything: {exc}"
        logger.error(error, exc_info=True)
        return False, error

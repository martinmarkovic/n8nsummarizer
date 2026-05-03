"""CLI runner helper for transcribe-anything.

Extracted from models/transcribe_model.py to keep subprocess and
encoding details in a single place.
"""

from __future__ import annotations

import os
import subprocess
import shlex
import sys
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
        # Use full path to transcribe-anything since subprocess with list doesn't search PATH
        transcribe_anything_path = "F:/Python scripts/n8nsummarizer/myenv/Scripts/transcribe-anything.exe"
        if not os.path.exists(transcribe_anything_path):
            # Fallback to just "transcribe-anything" if full path doesn't exist
            transcribe_anything_path = "transcribe-anything"
            logger.warning("transcribe-anything not found at expected path, using PATH lookup")
        
        # For YouTube URLs, don't quote them since transcribe-anything will extract the title
        # and the quotes would become part of the filename. For local file paths, quoting
        # is also not needed since we're using list format (not shell=True).
        input_path_for_cmd = input_path
        
        cmd = [
            transcribe_anything_path,
            input_path_for_cmd,
            "--device",
            device,
            "--output_dir",
            output_dir,
        ]
        
        # Add the virtual environment's Scripts directory to PATH
        # This ensures yt-dlp.exe can be found by transcribe-anything subprocess
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
        
        # Add the project's virtual environment Scripts directory to PATH
        # This ensures both transcribe-anything and yt-dlp.exe can be found
        project_scripts_dir = "F:/Python scripts/n8nsummarizer/myenv/Scripts"
        if os.path.exists(project_scripts_dir):
            env["PATH"] = project_scripts_dir + os.pathsep + env["PATH"]
            logger.debug("Added project virtual env scripts to PATH: %s", project_scripts_dir)
        else:
            logger.warning("Project scripts directory not found: %s", project_scripts_dir)
        
        # Also try to find yt-dlp in common locations
        common_yt_dlp_locations = [
            "F:/Python scripts/n8nsummarizer/myenv/Scripts",
            "C:/Python314/Scripts",
            "C:/Python3133/Scripts",
            "C:/Python39/Scripts",
        ]
        for yt_dlp_dir in common_yt_dlp_locations:
            if os.path.exists(yt_dlp_dir) and os.path.exists(os.path.join(yt_dlp_dir, "yt-dlp.exe")):
                if yt_dlp_dir not in env["PATH"]:
                    env["PATH"] = yt_dlp_dir + os.pathsep + env["PATH"]
                    logger.debug("Added yt-dlp location to PATH: %s", yt_dlp_dir)
                break
        
        # For logging, use the safe version to avoid shell interpretation in logs
        logger.info("Running: %s … --device %s", " ".join(cmd[:2]), device)
        logger.debug("Full command: %s", " ".join([shlex.quote(arg) if isinstance(arg, str) else str(arg) for arg in cmd]))

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

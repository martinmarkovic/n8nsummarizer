"""Output processing helpers for transcription results."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import logger


def process_outputs(
    output_dir: Path,
    base_name: str,
    keep_formats: List[str],
    source_type: str,
    url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[Dict]]:
    """Process transcription output files in ``output_dir``.

    This mirrors the behaviour of TranscribeModel._process_outputs:
    - Move/keep only selected formats
    - Delete unwanted formats
    - Load the best available transcript content
    """

    try:
        transcript_content: Optional[str] = None
        files_created: List[str] = []
        format_loaded: Optional[str] = None

        metadata: Dict[str, object] = {
            "base_name": base_name,
            "source_type": source_type,
            "url": url,
            "output_dir": str(output_dir),
            "files_kept": [],
            "files_deleted": [],
            "format_loaded": None,
        }

        output_extensions = [".txt", ".srt", ".vtt", ".json", ".tsv"]
        load_priority = [".srt", ".txt", ".vtt", ".json", ".tsv"]

        logger.info("Processing outputs in: %s", output_dir)

        for temp_file in output_dir.iterdir():
            if not temp_file.is_file():
                continue

            logger.debug("Found file: %s", temp_file.name)

            if not (
                temp_file.name.startswith("out.")
                or temp_file.suffix in output_extensions
            ):
                logger.debug("Skipping non-output file: %s", temp_file.name)
                continue

            if temp_file.name.startswith("out."):
                new_name = temp_file.name.replace("out.", f"{base_name}.")
            else:
                new_name = f"{base_name}{temp_file.suffix}"

            final_path = output_dir / new_name
            ext = temp_file.suffix.lower()

            logger.debug("Processing %s -> %s (keep=%s)", temp_file.name, new_name, ext in keep_formats)

            if ext in keep_formats:
                try:
                    temp_file.rename(final_path)
                    files_created.append(new_name)
                    metadata["files_kept"].append(new_name)

                    if transcript_content is None or (
                        ext in load_priority
                        and load_priority.index(ext)
                        <= load_priority.index(format_loaded or ext)
                    ):
                        with open(final_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if content.strip():
                                transcript_content = content
                                format_loaded = ext
                                logger.info(
                                    "Loaded transcript from: %s (%s chars)",
                                    ext,
                                    len(content),
                                )

                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to move %s to %s: %s",
                        temp_file.name,
                        final_path,
                        exc,
                        exc_info=True,
                    )

            else:
                try:
                    temp_file.unlink()
                    metadata["files_deleted"].append(new_name)
                    logger.info("Deleted unwanted format: %s", new_name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to delete %s: %s", temp_file.name, exc
                    )

        if transcript_content is None:
            logger.info("No transcript in kept formats, trying fallback…")
            for fallback_file in output_dir.iterdir():
                if not fallback_file.is_file():
                    continue
                ext = fallback_file.suffix.lower()
                if ext in output_extensions:
                    try:
                        logger.info("Trying fallback format: %s", ext)
                        with open(fallback_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if content.strip():
                                transcript_content = content
                                format_loaded = ext
                                logger.info(
                                    "Loaded transcript from fallback format: %s (%s chars)",
                                    ext,
                                    len(content),
                                )
                                break
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Failed to load %s: %s", fallback_file, exc
                        )

        metadata["format_loaded"] = format_loaded
        logger.info(
            "Output processing complete: %s files created, loaded from %s",
            len(files_created),
            format_loaded,
        )

        return transcript_content, metadata

    except Exception as exc:  # noqa: BLE001
        logger.error("Error processing outputs: %s", exc, exc_info=True)
        return None, None

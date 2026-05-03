"""
Bulk Summarizer Controller - v4.5 (.opus support)

Orchestrates bulk file summarization:
- Folder and file type validation (txt, srt, docx, pdf, opus)
- Background file discovery with multiple types
- Recursive subfolder scanning
- Sequential file processing
- N8N webhook communication
- Progress tracking and UI updates
- Error handling and logging
- Output folder and file management with improved naming
- Output format handling (separate/combined)
- Subfolder structure preservation in output

Version: 4.5
Updated: 2026-03-15
Changes:
- Added .opus file type support in _discover_files and _read_file
  .opus transcript files from transcribe-anything are stored as UTF-8 text
  so they are read identically to .txt / .srt files.
"""

from pathlib import Path
from threading import Thread
from typing import List, Tuple
from datetime import datetime
import logging
from docx import Document

from models.n8n_model import N8NModel
from utils.file_scanner import FileScanner
from utils.logger import logger


class BulkSummarizerController:
    """
    Orchestrates bulk file summarization.

    Handles:
    - Validation of source folder and file types
    - Discovery of matching files (txt, srt, docx, pdf, opus) with optional recursive scanning
    - Background processing with threading
    - N8N integration for summarization
    - Output folder and file management
    - Subfolder structure preservation
    - Real-time progress updates
    - Error handling and recovery
    - Separate and combined output formats
    """

    def __init__(self, view):
        self.view = view
        self.n8n_model = N8NModel()
        self.is_processing = False

        self.view.set_on_start_requested(self.handle_start_processing)
        self.view.set_on_cancel_requested(self.handle_cancel_processing)

        logger.info("BulkSummarizerController initialized")

    # ------------------------------------------------------------------
    # Public handlers
    # ------------------------------------------------------------------

    def handle_start_processing(self):
        source_folder = self.view.get_source_folder()
        if not source_folder:
            self.view.append_log("Error: No folder selected", "error")
            return

        if not Path(source_folder).exists():
            self.view.append_log(f"Error: Folder not found: {source_folder}", "error")
            return

        file_types = self.view.get_file_types()
        if not file_types:
            self.view.append_log("Error: At least one file type must be selected", "error")
            return

        output_formats = self.view.get_output_formats()
        if not output_formats['separate'] and not output_formats['combined']:
            self.view.append_log("Error: At least one output format must be selected", "error")
            return

        recursive = self.view.get_recursive_option()
        files = self._discover_files(source_folder, file_types, recursive)
        if not files:
            self.view.append_log(
                f"Error: No files found matching selected types: {', '.join(file_types)}",
                "error"
            )
            return

        output_folder = self.view.get_output_folder()
        if not output_folder:
            self.view.append_log("Error: Invalid output folder", "error")
            return

        self.view.append_log(f"Found {len(files)} files to process", "info")
        self.view.append_log(
            f"Output formats: {'separate' if output_formats['separate'] else ''} "
            f"{'combined' if output_formats['combined'] else ''}",
            "info"
        )
        if recursive:
            self.view.append_log("Recursive scanning enabled - processing subfolders", "info")

        self.view.set_processing_enabled(False)
        self.is_processing = True

        logger.info(
            f"Starting bulk processing: {len(files)} files, output: {output_folder}, "
            f"recursive: {recursive}"
        )

        thread = Thread(
            target=self._process_folder_background,
            args=(source_folder, files, output_folder, output_formats, recursive),
            daemon=True
        )
        thread.start()

    def handle_cancel_processing(self):
        self.is_processing = False
        self.view.append_log("Processing stopped by user", "warning")
        logger.info("Bulk processing cancelled by user")

    # ------------------------------------------------------------------
    # File Discovery
    # ------------------------------------------------------------------

    def _discover_files(self, folder: str, file_types: List[str],
                        recursive: bool = False) -> List[Path]:
        """
        Discover all matching files in folder.

        Supported types: txt, srt, docx, pdf, opus (NEW v4.5)
        """
        # Patterns for file discovery
        patterns = {
            'txt':  ['*.txt'],
            'srt':  ['*.srt'],
            'docx': ['*.docx'],
            'pdf':  ['*.pdf'],
            'opus': ['*.opus'],
        }

        try:
            # Filter patterns to only include selected file types
            selected_patterns = {}
            for file_type in file_types:
                if file_type in patterns:
                    selected_patterns[file_type] = patterns[file_type]

            # Use FileScanner for unified file discovery
            files = FileScanner.scan_with_patterns(folder, selected_patterns, recursive)
            
            logger.info(
                f"Discovered {len(files)} total files matching types: {file_types}, "
                f"recursive={recursive}"
            )
            return files

        except Exception as e:
            logger.error(f"Error discovering files: {str(e)}")
            return []

    # ------------------------------------------------------------------
    # Background Processing
    # ------------------------------------------------------------------

    def _process_folder_background(
        self, source_folder: str, files: List[Path],
        output_folder: str, output_formats: dict, recursive: bool = False
    ):
        try:
            total = len(files)
            output_path = self._create_output_folder(source_folder, output_folder)

            successful = 0
            failed = 0
            failed_files = []
            combined_content = []

            logger.info(
                f"Background processing started: {total} files, output: {output_path}, "
                f"recursive: {recursive}"
            )

            for idx, file_path in enumerate(files, 1):
                if not self.is_processing:
                    self.view.root.after(
                        0, self.view.append_log, "Processing stopped by user", "warning"
                    )
                    break

                try:
                    self.view.root.after(0, self.view.set_current_file, file_path.name)

                    content = self._read_file(file_path)
                    if not content or content.strip() == "":
                        raise ValueError("File is empty")

                    logger.info(f"Processing {idx}/{total}: {file_path.name} ({len(content)} chars)")

                    success, summary, error = self.n8n_model.send_content(
                        file_name=file_path.stem,
                        content=content
                    )

                    if success and summary:
                        if recursive:
                            relative_path = file_path.parent.relative_to(Path(source_folder))
                            current_output_folder = output_path / relative_path
                            current_output_folder.mkdir(parents=True, exist_ok=True)
                        else:
                            current_output_folder = output_path

                        if output_formats['separate']:
                            self._save_summary(current_output_folder, file_path, summary)

                        if output_formats['combined']:
                            display_name = file_path.name
                            if recursive:
                                rel = file_path.parent.relative_to(Path(source_folder))
                                display_name = str(rel / file_path.name)
                            combined_content.append({
                                'filename': display_name,
                                'summary': summary
                            })

                        self.view.root.after(
                            0, self.view.append_log,
                            f"{file_path.name} - Completed", "success"
                        )
                        successful += 1
                        logger.info(f"Successfully processed {file_path.name}")
                    else:
                        raise Exception(error or "Unknown error from N8N")

                except Exception as e:
                    error_msg = str(e)[:60]
                    logger.error(f"Error processing {file_path.name}: {str(e)}")
                    self.view.root.after(
                        0, self.view.append_log,
                        f"{file_path.name} - Failed: {error_msg}", "error"
                    )
                    failed += 1
                    failed_files.append(file_path.name)

                finally:
                    self.view.root.after(0, self.view.update_progress, idx, total)

            if output_formats['combined'] and combined_content:
                try:
                    self._save_combined_summary(output_path, combined_content)
                    self.view.root.after(
                        0, self.view.append_log, "Combined summary file created", "success"
                    )
                except Exception as e:
                    logger.error(f"Error creating combined summary: {str(e)}")
                    self.view.root.after(
                        0, self.view.append_log,
                        f"Error creating combined file: {str(e)}", "error"
                    )

        finally:
            self.view.root.after(
                0, self._show_completion_summary,
                total, successful, failed, failed_files
            )

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    def _create_output_folder(self, source_folder: str, output_location: str) -> Path:
        try:
            output_path = Path(output_location)
            source_path = Path(source_folder)
            source_folder_name = source_path.name

            if str(output_path) == str(source_path.parent):
                output_path = output_path / f"{source_folder_name} - Summarized"
                logger.info(f"Using default output location: {source_folder_name} - Summarized")

            output_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output folder: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error creating output folder: {str(e)}")
            raise

    def _read_file(self, file_path: Path) -> str:
        """
        Read content from supported file types.

        Supported: .txt, .srt, .docx, .pdf, .opus (NEW v4.5)

        .opus files produced by transcribe-anything are plain UTF-8 text files
        (transcript text stored with .opus extension), so they are read the
        same way as .txt / .srt files.
        """
        try:
            suffix = file_path.suffix.lower()

            if suffix in (".txt", ".srt", ".opus"):  # .opus treated as UTF-8 text
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    logger.debug(f"Read {file_path.name} ({suffix}): {len(content)} chars")
                    return content

            elif suffix == ".docx":
                doc = Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                logger.debug(f"Read {file_path.name} (DOCX): {len(content)} chars")
                return content

            elif suffix == ".pdf":
                logger.warning(f"PDF support not yet implemented: {file_path.name}")
                return f"[PDF file: {file_path.name} - extraction not yet supported]"

            else:
                raise ValueError(f"Unsupported file type: {suffix}")

        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {str(e)}")
            raise

    def _save_summary(self, output_folder: Path, source_file: Path, summary: str) -> Path:
        try:
            output_path = output_folder / f"{source_file.stem}_summary.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Saved summary: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving summary for {source_file.name}: {str(e)}")
            raise

    def _save_combined_summary(self, output_folder: Path, summaries: List[dict]) -> Path:
        try:
            output_path = output_folder / "COMBINED_SUMMARY.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(
                    f"Combined Summary - Generated "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write("=" * 60 + "\n\n")
                for item in summaries:
                    f.write(f"===== {item['filename']} =====\n")
                    f.write(item['summary'])
                    f.write("\n\n")
            logger.info(f"Saved combined summary: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving combined summary: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def _show_completion_summary(
        self, total: int, successful: int, failed: int, failed_files: List[str]
    ):
        self.view.set_processing_enabled(True)
        self.is_processing = False

        self.view.append_log("=" * 50, "info")
        self.view.append_log("Processing Complete!", "success")
        self.view.append_log(
            f"Total: {total} | Successful: {successful} | Failed: {failed}", "info"
        )

        if failed > 0 and failed_files:
            self.view.append_log(f"Failed files: {', '.join(failed_files)}", "warning")

        self.view.append_log("=" * 50, "info")

        logger.info(
            f"Bulk processing complete: {successful}/{total} successful, {failed} failed"
        )
        if failed > 0:
            logger.warning(f"Failed files: {failed_files}")

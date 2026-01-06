"""
Bulk Summarizer Controller - Phase 4.5 Transcript Saving Support

Orchestrates bulk file summarization:
- Folder and file type validation (txt, srt, docx, pdf)
- Background file discovery with multiple types
- Recursive subfolder scanning (v4.7)
- Sequential file processing
- N8N webhook communication
- Progress tracking and UI updates
- Error handling and logging
- Output folder and file management with improved naming
- Output format handling (separate/combined)
- Subfolder structure preservation in output
- Transcript saving with dual format support (NEW in v4.8)

Version: 4.5
Updated: 2026-01-06
Changes:
- Added transcript extraction and saving
- Supports .srt and optional .txt formats
- Creates separate "- Transcripts" folder
- Preserves subfolder structure in transcripts
- Transcript extraction and summarization both working
"""

from pathlib import Path
from threading import Thread
from typing import List, Tuple
from datetime import datetime
import logging
from docx import Document

from models.n8n_model import N8NModel
from utils.logger import logger


class BulkSummarizerController:
    """
    Orchestrates bulk file summarization with transcript saving support.
    
    Handles:
    - Validation of source folder and file types
    - Discovery of matching files (txt, srt, docx, pdf) with optional recursive scanning
    - Background processing with threading
    - N8N integration for summarization
    - Output folder and file management
    - Subfolder structure preservation
    - Transcript extraction and saving (SRT + optional TXT)
    - Real-time progress updates
    - Error handling and recovery
    - Separate and combined output formats
    """
    
    def __init__(self, view):
        """
        Initialize bulk summarizer controller.
        
        Args:
            view: BulkSummarizerTab instance
        """
        self.view = view
        self.n8n_model = N8NModel()
        self.is_processing = False
        
        # Register callbacks
        self.view.set_on_start_requested(self.handle_start_processing)
        self.view.set_on_cancel_requested(self.handle_cancel_processing)
        
        logger.info("BulkSummarizerController initialized")
    
    def handle_start_processing(self):
        """
        User clicked Start - validate inputs and launch processing.
        
        Validation:
        - Folder exists and is accessible
        - At least one file of selected type exists
        - At least one output format selected
        - User hasn't already started processing
        """
        
        # Get and validate inputs
        source_folder = self.view.get_source_folder()
        if not source_folder:
            self.view.append_log("Error: No folder selected", "error")
            return
        
        if not Path(source_folder).exists():
            self.view.append_log(f"Error: Folder not found: {source_folder}", "error")
            return
        
        # Get file types
        file_types = self.view.get_file_types()
        if not file_types:
            self.view.append_log("Error: At least one file type must be selected", "error")
            return
        
        # Get output formats
        output_formats = self.view.get_output_formats()
        if not output_formats['separate'] and not output_formats['combined']:
            self.view.append_log("Error: At least one output format must be selected", "error")
            return
        
        # v4.7: Get recursive option
        recursive = self.view.get_recursive_option()
        
        # v4.8: Get transcript options
        transcript_options = self.view.get_transcript_options()
        
        # Discover files
        files = self._discover_files(source_folder, file_types, recursive)
        if not files:
            self.view.append_log(f"Error: No files found matching selected types: {', '.join(file_types)}", "error")
            return
        
        # Validate output location
        output_folder = self.view.get_output_folder()
        if not output_folder:
            self.view.append_log("Error: Invalid output folder", "error")
            return
        
        # Update UI and launch background thread
        self.view.append_log(f"Found {len(files)} files to process", "info")
        self.view.append_log(f"Output formats: {'separate' if output_formats['separate'] else ''} {'combined' if output_formats['combined'] else ''}", "info")
        if recursive:
            self.view.append_log(f"Recursive scanning enabled - processing subfolders", "info")
        if transcript_options['save']:
            formats = ["SRT"]
            if transcript_options['format_txt']:
                formats.append("TXT")
            self.view.append_log(f"Transcript saving enabled - formats: {', '.join(formats)}", "info")
        
        self.view.set_processing_enabled(False)
        self.is_processing = True
        
        logger.info(f"Starting bulk processing: {len(files)} files, output: {output_folder}, recursive: {recursive}")
        logger.info(f"File types: {file_types}, Output formats: separate={output_formats['separate']}, combined={output_formats['combined']}")
        logger.info(f"Transcript saving: {transcript_options['save']}, SRT: {transcript_options['format_srt']}, TXT: {transcript_options['format_txt']}")
        
        # Launch background worker thread
        thread = Thread(
            target=self._process_folder_background,
            args=(source_folder, files, output_folder, output_formats, recursive, transcript_options),
            daemon=True
        )
        thread.start()
    
    def handle_cancel_processing(self):
        """
        User clicked Cancel - stop background processing.
        """
        self.is_processing = False
        self.view.append_log("Processing stopped by user", "warning")
        logger.info("Bulk processing cancelled by user")
    
    # File Discovery
    
    def _discover_files(self, folder: str, file_types: List[str], recursive: bool = False) -> List[Path]:
        """
        Discover all matching files in folder.
        
        v4.7: Added recursive parameter for subfolder scanning.
        
        Args:
            folder: Path to folder
            file_types: List of file types to search for ('txt', 'srt', 'docx', 'pdf')
            recursive: If True, scan subfolders recursively
        
        Returns:
            Sorted list of Path objects matching selected file types
        """
        folder_path = Path(folder)
        files = []
        
        try:
            # Map file type to glob pattern
            patterns = {
                'txt': '*.txt',
                'srt': '*.srt',
                'docx': '*.docx',
                'pdf': '*.pdf'
            }
            
            # Discover files for each selected type
            for file_type in file_types:
                if file_type in patterns:
                    if recursive:
                        # v4.7: Use rglob for recursive scanning
                        matching = list(folder_path.rglob(patterns[file_type]))
                        logger.debug(f"Found {len(matching)} {file_type} files (recursive)")
                    else:
                        # Normal glob for current folder only
                        matching = list(folder_path.glob(patterns[file_type]))
                        logger.debug(f"Found {len(matching)} {file_type} files")
                    files.extend(matching)
            
            # Sort and remove duplicates
            files = sorted(set(files))
            
            logger.info(f"Discovered {len(files)} total files matching types: {file_types}, recursive={recursive}")
            return files
        
        except Exception as e:
            logger.error(f"Error discovering files: {str(e)}")
            return []
    
    # Background Processing
    
    def _process_folder_background(self, source_folder: str, files: List[Path], 
                                   output_folder: str, output_formats: dict, 
                                   recursive: bool = False, transcript_options: dict = None):
        """
        Background worker thread for bulk processing.
        
        v4.8: Added transcript saving support.
        
        Executes:
        1. Create output folder structure (summaries and transcripts)
        2. For each file:
           - Update UI with current file
           - Read file content
           - Send to N8N for summarization
           - Save summary (separate and/or combined)
           - Extract and save transcript if enabled
           - Preserve subfolder structure in output
           - Log result (success/error)
        3. Generate combined file if selected
        4. Show completion summary
        
        Args:
            source_folder: Path to source folder
            files: List of file paths to process
            output_folder: Path to output folder
            output_formats: Dict with 'separate' and 'combined' flags
            recursive: If True, preserve subfolder structure in output
            transcript_options: Dict with 'save', 'format_srt', 'format_txt' flags
        """
        if transcript_options is None:
            transcript_options = {'save': False, 'format_srt': True, 'format_txt': False}
        
        try:
            total = len(files)
            output_path = self._create_output_folder(source_folder, output_folder)
            
            # v4.8: Create transcripts folder if enabled
            transcript_path = None
            if transcript_options['save']:
                transcript_path = self._create_transcript_folder(source_folder, output_folder)
            
            successful = 0
            failed = 0
            failed_files = []
            combined_content = []  # For combined output
            
            logger.info(f"Background processing started: {total} files, output: {output_path}, recursive: {recursive}")
            if transcript_options['save']:
                logger.info(f"Transcript saving: SRT={transcript_options['format_srt']}, TXT={transcript_options['format_txt']}")
            
            for idx, file_path in enumerate(files, 1):
                # Check if user cancelled
                if not self.is_processing:
                    self.view.root.after(
                        0,
                        self.view.append_log,
                        "Processing stopped by user",
                        "warning"
                    )
                    break
                
                try:
                    # Update UI with current file
                    self.view.root.after(
                        0,
                        self.view.set_current_file,
                        file_path.name
                    )
                    
                    # Read file content
                    content = self._read_file(file_path)
                    if not content or content.strip() == "":
                        raise ValueError("File is empty")
                    
                    logger.info(f"Processing {idx}/{total}: {file_path.name} ({len(content)} chars)")
                    
                    # Send to N8N for summarization
                    success, summary, error = self.n8n_model.send_content(
                        file_name=file_path.stem,
                        content=content
                    )
                    
                    if success and summary:
                        # v4.7: Create output subfolder structure if recursive
                        if recursive:
                            # Get relative path from source folder to preserve structure
                            relative_path = file_path.parent.relative_to(Path(source_folder))
                            current_output_folder = output_path / relative_path
                            current_output_folder.mkdir(parents=True, exist_ok=True)
                            logger.debug(f"Created output subfolder: {current_output_folder}")
                        else:
                            current_output_folder = output_path
                        
                        # Save separate file if selected
                        if output_formats['separate']:
                            self._save_summary(current_output_folder, file_path, summary)
                        
                        # Add to combined content if selected
                        if output_formats['combined']:
                            # Include relative path in combined output for clarity
                            display_name = file_path.name
                            if recursive:
                                relative_path = file_path.parent.relative_to(Path(source_folder))
                                display_name = str(relative_path / file_path.name)
                            
                            combined_content.append({
                                'filename': display_name,
                                'summary': summary
                            })
                        
                        # v4.8: Save transcripts if enabled
                        if transcript_options['save'] and transcript_path:
                            if recursive:
                                relative_path = file_path.parent.relative_to(Path(source_folder))
                                current_transcript_folder = transcript_path / relative_path
                                current_transcript_folder.mkdir(parents=True, exist_ok=True)
                            else:
                                current_transcript_folder = transcript_path
                            
                            # Save as SRT (default)
                            if transcript_options['format_srt']:
                                self._save_transcript_srt(current_transcript_folder, file_path, content)
                            
                            # Save as TXT if selected
                            if transcript_options['format_txt']:
                                self._save_transcript_txt(current_transcript_folder, file_path, content)
                        
                        # Log success
                        self.view.root.after(
                            0,
                            self.view.append_log,
                            f"{file_path.name} - Completed",
                            "success"
                        )
                        successful += 1
                        logger.info(f"Successfully processed {file_path.name}")
                    else:
                        # N8N returned error
                        error_msg = error or "Unknown error from N8N"
                        raise Exception(error_msg)
                
                except Exception as e:
                    # File processing failed - log and continue
                    error_msg = str(e)[:60]  # Truncate long errors
                    logger.error(f"Error processing {file_path.name}: {str(e)}")
                    
                    self.view.root.after(
                        0,
                        self.view.append_log,
                        f"{file_path.name} - Failed: {error_msg}",
                        "error"
                    )
                    
                    failed += 1
                    failed_files.append(file_path.name)
                
                finally:
                    # Update progress bar
                    self.view.root.after(
                        0,
                        self.view.update_progress,
                        idx,
                        total
                    )
            
            # Generate combined file if selected and there's content
            if output_formats['combined'] and combined_content:
                try:
                    self._save_combined_summary(output_path, combined_content)
                    self.view.root.after(
                        0,
                        self.view.append_log,
                        "Combined summary file created",
                        "success"
                    )
                except Exception as e:
                    logger.error(f"Error creating combined summary: {str(e)}")
                    self.view.root.after(
                        0,
                        self.view.append_log,
                        f"Error creating combined file: {str(e)}",
                        "error"
                    )
        
        finally:
            # Show completion summary
            self.view.root.after(
                0,
                self._show_completion_summary,
                total,
                successful,
                failed,
                failed_files
            )
    
    # File Operations
    
    def _create_output_folder(self, source_folder: str, output_location: str) -> Path:
        """
        Create output folder structure for summaries.
        
        Output folder naming: [SourceFolderName] - Summarized
        
        Args:
            source_folder: Path to source folder
            output_location: Output folder path
        
        Returns:
            Path object of created output folder
        """
        try:
            output_path = Path(output_location)
            source_path = Path(source_folder)
            
            # Get the source folder name
            source_folder_name = source_path.name
            
            # Check if this is the default location (parent folder)
            if str(output_path) == str(source_path.parent):
                # Create subfolder with original name + "- Summarized"
                output_path = output_path / f"{source_folder_name} - Summarized"
                logger.info(f"Using default output location: {source_folder_name} - Summarized")
            
            output_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output folder: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating output folder: {str(e)}")
            raise
    
    def _create_transcript_folder(self, source_folder: str, output_location: str) -> Path:
        """
        Create output folder structure for transcripts (v4.8).
        
        v4.8: New method for transcript folder creation.
        
        Output folder naming: [SourceFolderName] - Transcripts
        Located at same level as summaries folder.
        
        Args:
            source_folder: Path to source folder
            output_location: Output folder path
        
        Returns:
            Path object of created transcript folder
        """
        try:
            output_path = Path(output_location)
            source_path = Path(source_folder)
            
            # Get the source folder name
            source_folder_name = source_path.name
            
            # Check if this is the default location (parent folder)
            if str(output_path) == str(source_path.parent):
                # Create subfolder with original name + "- Transcripts"
                output_path = output_path / f"{source_folder_name} - Transcripts"
                logger.info(f"Using default transcript location: {source_folder_name} - Transcripts")
            else:
                # For custom output location, append "- Transcripts"
                output_path = output_path / f"{source_folder_name} - Transcripts"
            
            output_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created transcript folder: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating transcript folder: {str(e)}")
            raise
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read content from supported file types.
        
        Supported: .txt, .srt, .docx, .pdf
        
        Args:
            file_path: Path to file
        
        Returns:
            File content as string
        
        Raises:
            ValueError: If file type not supported
        """
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    logger.debug(f"Read {file_path.name}: {len(content)} chars")
                    return content
            
            elif suffix == ".srt":
                # SRT files are text-based subtitle format
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    logger.debug(f"Read {file_path.name} (SRT): {len(content)} chars")
                    return content
            
            elif suffix == ".docx":
                doc = Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                logger.debug(f"Read {file_path.name} (DOCX): {len(content)} chars")
                return content
            
            elif suffix == ".pdf":
                # PDF support requires PyPDF2 or pdfplumber
                # For now, return placeholder
                # TODO: Implement PDF text extraction
                logger.warning(f"PDF support not yet implemented: {file_path.name}")
                return f"[PDF file: {file_path.name} - extraction not yet supported]"
            
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
        
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {str(e)}")
            raise
    
    def _save_summary(self, output_folder: Path, source_file: Path, summary: str) -> Path:
        """
        Save individual summary file.
        
        Filename: "[OriginalFilename]_summary.txt"
        
        Args:
            output_folder: Path to output folder
            source_file: Path to source file
            summary: Summary text from N8N
        
        Returns:
            Path object of saved summary file
        """
        try:
            output_path = output_folder / f"{source_file.stem}_summary.txt"
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(summary)
            
            logger.info(f"Saved summary: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error saving summary for {source_file.name}: {str(e)}")
            raise
    
    def _save_transcript_srt(self, output_folder: Path, source_file: Path, content: str) -> Path:
        """
        Save transcript as SRT format (v4.8).
        
        v4.8: New method for saving transcripts in SRT format.
        
        Filename: "[OriginalFilename].srt"
        Format: SRT subtitle format (simple text for now, can be enhanced with timestamps)
        
        Args:
            output_folder: Path to output folder
            source_file: Path to source file
            content: Original file content to save as transcript
        
        Returns:
            Path object of saved transcript file
        """
        try:
            output_path = output_folder / f"{source_file.stem}.srt"
            
            with open(output_path, "w", encoding="utf-8") as f:
                # Simple SRT format: just save the content
                # Future enhancement: parse content and add timestamps
                f.write(content)
            
            logger.info(f"Saved transcript (SRT): {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error saving transcript (SRT) for {source_file.name}: {str(e)}")
            raise
    
    def _save_transcript_txt(self, output_folder: Path, source_file: Path, content: str) -> Path:
        """
        Save transcript as TXT format (v4.8).
        
        v4.8: New method for saving transcripts in TXT format.
        
        Filename: "[OriginalFilename].txt"
        Format: Plain text
        
        Args:
            output_folder: Path to output folder
            source_file: Path to source file
            content: Original file content to save as transcript
        
        Returns:
            Path object of saved transcript file
        """
        try:
            output_path = output_folder / f"{source_file.stem}.txt"
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Saved transcript (TXT): {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error saving transcript (TXT) for {source_file.name}: {str(e)}")
            raise
    
    def _save_combined_summary(self, output_folder: Path, summaries: List[dict]) -> Path:
        """
        Save combined summary file with all summaries.
        
        Filename: "COMBINED_SUMMARY.txt"
        Format:
            ===== [filename1] =====
            [summary1]
            
            ===== [filename2] =====
            [summary2]
        
        v4.7: Includes relative paths when recursive scanning was used.
        
        Args:
            output_folder: Path to output folder
            summaries: List of dicts with 'filename' and 'summary'
        
        Returns:
            Path object of saved combined file
        """
        try:
            output_path = output_folder / "COMBINED_SUMMARY.txt"
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"Combined Summary - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
    
    # Completion Handling
    
    def _show_completion_summary(self, total: int, successful: int, failed: int, 
                                 failed_files: List[str]):
        """
        Show processing completion summary.
        
        Called after background thread finishes.
        
        Args:
            total: Total files processed
            successful: Files successfully summarized
            failed: Files that failed
            failed_files: List of failed file names
        """
        # Re-enable processing buttons
        self.view.set_processing_enabled(True)
        self.is_processing = False
        
        # Log summary
        self.view.append_log("=" * 50, "info")
        self.view.append_log(f"Processing Complete!", "success")
        self.view.append_log(
            f"Total: {total} | Successful: {successful} | Failed: {failed}",
            "info"
        )
        
        if failed > 0 and failed_files:
            self.view.append_log(
                f"Failed files: {', '.join(failed_files)}",
                "warning"
            )
        
        self.view.append_log("=" * 50, "info")
        
        # Log to file
        logger.info(f"Bulk processing complete: {successful}/{total} successful, {failed} failed")
        if failed > 0:
            logger.warning(f"Failed files: {failed_files}")

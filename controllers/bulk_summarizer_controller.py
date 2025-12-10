"""
Bulk Summarizer Controller - Phase 4.1 Implementation

Orchestrates bulk file summarization:
- Folder and file type validation
- Background file discovery
- Sequential file processing
- N8N webhook communication
- Progress tracking and UI updates
- Error handling and logging
- Output folder and file management

Version: 4.1
Created: 2025-12-10
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
    Orchestrates bulk file summarization.
    
    Handles:
    - Validation of source folder and file types
    - Discovery of matching files
    - Background processing with threading
    - N8N integration for summarization
    - Output folder and file management
    - Real-time progress updates
    - Error handling and recovery
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
        
        # Discover files
        files = self._discover_files(source_folder)
        if not files:
            self.view.append_log("Error: No matching files found in folder", "error")
            return
        
        # Update UI and launch background thread
        self.view.append_log(f"Found {len(files)} files to process", "info")
        self.view.set_processing_enabled(False)
        self.is_processing = True
        
        logger.info(f"Starting bulk processing: {len(files)} files")
        
        # Launch background worker thread
        thread = Thread(
            target=self._process_folder_background,
            args=(source_folder, files),
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
    
    def _discover_files(self, folder: str) -> List[Path]:
        """
        Discover all matching files in folder.
        
        Returns:
            Sorted list of Path objects matching selected file type
        """
        folder_path = Path(folder)
        file_type = self.view.get_file_type()
        
        try:
            if file_type == "txt":
                files = sorted(folder_path.glob("*.txt"))
            elif file_type == "docx":
                files = sorted(folder_path.glob("*.docx"))
            else:  # both
                files = sorted(folder_path.glob("*.txt")) + sorted(folder_path.glob("*.docx"))
            
            logger.info(f"Discovered {len(files)} files in {folder}")
            return files
        
        except Exception as e:
            logger.error(f"Error discovering files: {str(e)}")
            return []
    
    # Background Processing
    
    def _process_folder_background(self, source_folder: str, files: List[Path]):
        """
        Background worker thread for bulk processing.
        
        Executes:
        1. Create output folder
        2. For each file:
           - Update UI with current file
           - Read file content
           - Send to N8N for summarization
           - Save summary to output folder
           - Log result (success/error)
        3. Show completion summary
        
        Args:
            source_folder: Path to source folder
            files: List of file paths to process
        """
        try:
            total = len(files)
            output_folder = self._create_output_folder(source_folder)
            
            successful = 0
            failed = 0
            failed_files = []
            
            logger.info(f"Background processing started: {total} files, output: {output_folder}")
            
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
                        # Save summary to output folder
                        self._save_summary(output_folder, file_path, summary)
                        
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
    
    def _create_output_folder(self, source_folder: str) -> Path:
        """
        Create output folder: "[SourceFolderName] - Summarized"
        
        Located at same level as source folder.
        
        Args:
            source_folder: Path to source folder
        
        Returns:
            Path object of created output folder
        """
        source_path = Path(source_folder)
        output_name = f"{source_path.name} - Summarized"
        output_path = source_path.parent / output_name
        
        try:
            output_path.mkdir(exist_ok=True)
            logger.info(f"Created output folder: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating output folder: {str(e)}")
            raise
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read content from .txt or .docx file.
        
        Args:
            file_path: Path to file
        
        Returns:
            File content as string
        
        Raises:
            ValueError: If file type not supported
        """
        try:
            if file_path.suffix.lower() == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    logger.debug(f"Read {file_path.name}: {len(content)} chars")
                    return content
            
            elif file_path.suffix.lower() == ".docx":
                doc = Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                logger.debug(f"Read {file_path.name}: {len(content)} chars")
                return content
            
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {str(e)}")
            raise
    
    def _save_summary(self, output_folder: Path, source_file: Path, summary: str) -> Path:
        """
        Save summary to output folder.
        
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

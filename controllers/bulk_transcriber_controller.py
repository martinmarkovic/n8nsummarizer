"""
Bulk Transcriber Controller - Phase 5.0 Bulk Media Transcription

Orchestrates bulk media file transcription:
- Folder and media type validation (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
- Background file discovery with multiple media types
- Recursive subfolder scanning (NEW in v5.0)
- Sequential file processing
- N8N webhook communication for transcription
- Progress tracking and UI updates
- Error handling and logging
- Output folder and file management
- Output format handling (SRT, TXT, VTT, JSON)
- Subfolder structure preservation in output

Version: 1.0
Created: 2026-01-06
Phase: v5.0 - Bulk Transcription
"""

from pathlib import Path
from threading import Thread
from typing import List, Dict
from datetime import datetime
import logging

from models.n8n_model import N8NModel
from utils.logger import logger


class BulkTranscriberController:
    """
    Orchestrates bulk media file transcription with recursive subfolder support.
    
    Handles:
    - Validation of source folder and media types
    - Discovery of matching files (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm) with optional recursive scanning
    - Background processing with threading
    - N8N integration for transcription
    - Output folder and file management
    - Subfolder structure preservation
    - Real-time progress updates
    - Error handling and recovery
    - Multiple output formats (SRT, TXT, VTT, JSON)
    """
    
    def __init__(self, view):
        """
        Initialize bulk transcriber controller.
        
        Args:
            view: BulkTranscriberTab instance
        """
        self.view = view
        self.n8n_model = N8NModel()
        self.is_processing = False
        
        # Register callbacks
        self.view.set_on_start_requested(self.handle_start_processing)
        self.view.set_on_cancel_requested(self.handle_cancel_processing)
        
        logger.info("BulkTranscriberController initialized (Phase 5.0)")
    
    def handle_start_processing(self):
        """
        User clicked Start - validate inputs and launch processing.
        
        Validation:
        - Folder exists and is accessible
        - At least one file of selected media type exists
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
        
        # Get media types
        media_types = self.view.get_media_types()
        if not media_types:
            self.view.append_log("Error: At least one media format must be selected", "error")
            return
        
        # Get output formats
        output_formats = self.view.get_output_formats()
        if not any(output_formats.values()):
            self.view.append_log("Error: At least one output format must be selected", "error")
            return
        
        # Get recursive option
        recursive = self.view.get_recursive_option()
        
        # Discover files
        files = self._discover_files(source_folder, media_types, recursive)
        if not files:
            self.view.append_log(f"Error: No media files found matching selected types: {', '.join(media_types)}", "error")
            return
        
        # Validate output location
        output_folder = self.view.get_output_folder()
        if not output_folder:
            self.view.append_log("Error: Invalid output folder", "error")
            return
        
        # Update UI and launch background thread
        self.view.append_log(f"Found {len(files)} media files to transcribe", "info")
        
        # Show selected output formats
        selected_formats = []
        if output_formats.get('srt'):
            selected_formats.append('SRT')
        if output_formats.get('txt'):
            selected_formats.append('TXT')
        if output_formats.get('vtt'):
            selected_formats.append('VTT')
        if output_formats.get('json'):
            selected_formats.append('JSON')
        
        self.view.append_log(f"Output formats: {', '.join(selected_formats)}", "info")
        
        if recursive:
            self.view.append_log(f"Recursive scanning enabled - processing subfolders", "info")
        
        self.view.set_processing_enabled(False)
        self.is_processing = True
        
        logger.info(f"Starting bulk transcription: {len(files)} files, output: {output_folder}, recursive: {recursive}")
        logger.info(f"Media types: {media_types}, Output formats: {output_formats}")
        
        # Launch background worker thread
        thread = Thread(
            target=self._process_folder_background,
            args=(source_folder, files, output_folder, output_formats, recursive),
            daemon=True
        )
        thread.start()
    
    def handle_cancel_processing(self):
        """
        User clicked Cancel - stop background processing.
        """
        self.is_processing = False
        self.view.append_log("Processing stopped by user", "warning")
        logger.info("Bulk transcription cancelled by user")
    
    # File Discovery
    
    def _discover_files(self, folder: str, media_types: List[str], recursive: bool = False) -> List[Path]:
        """
        Discover all matching media files in folder.
        
        Args:
            folder: Path to folder
            media_types: List of media types to search for
                        Video: 'mp4', 'mov', 'avi', 'mkv', 'webm'
                        Audio: 'mp3', 'wav', 'm4a', 'flac', 'aac', 'wma'
            recursive: If True, scan subfolders recursively
        
        Returns:
            Sorted list of Path objects matching selected media types
        """
        folder_path = Path(folder)
        files = []
        
        try:
            # Map media type to glob pattern
            patterns = {
                'mp4': '*.mp4',
                'mov': '*.mov',
                'avi': '*.avi',
                'mkv': '*.mkv',
                'webm': '*.webm',
                'mp3': '*.mp3',
                'wav': '*.wav',
                'm4a': '*.m4a',
                'flac': '*.flac',
                'aac': '*.aac',
                'wma': '*.wma'
            }
            
            # Discover files for each selected type
            for media_type in media_types:
                if media_type in patterns:
                    if recursive:
                        # Use rglob for recursive scanning
                        matching = list(folder_path.rglob(patterns[media_type]))
                        logger.debug(f"Found {len(matching)} {media_type} files (recursive)")
                    else:
                        # Normal glob for current folder only
                        matching = list(folder_path.glob(patterns[media_type]))
                        logger.debug(f"Found {len(matching)} {media_type} files")
                    files.extend(matching)
            
            # Sort and remove duplicates
            files = sorted(set(files))
            
            logger.info(f"Discovered {len(files)} total media files matching types: {media_types}, recursive={recursive}")
            return files
        
        except Exception as e:
            logger.error(f"Error discovering files: {str(e)}")
            return []
    
    # Background Processing
    
    def _process_folder_background(self, source_folder: str, files: List[Path], 
                                   output_folder: str, output_formats: Dict, recursive: bool = False):
        """
        Background worker thread for bulk transcription.
        
        Executes:
        1. Create output folder structure
        2. For each file:
           - Update UI with current file
           - Send to N8N for transcription
           - Save transcript in selected formats
           - Preserve subfolder structure in output
           - Log result (success/error)
        3. Show completion summary
        
        Args:
            source_folder: Path to source folder
            files: List of media file paths to process
            output_folder: Path to output folder
            output_formats: Dict with 'srt', 'txt', 'vtt', 'json' flags
            recursive: If True, preserve subfolder structure in output
        """
        try:
            total = len(files)
            output_path = self._create_output_folder(source_folder, output_folder)
            
            successful = 0
            failed = 0
            failed_files = []
            
            logger.info(f"Background transcription started: {total} files, output: {output_path}, recursive: {recursive}")
            
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
                    
                    logger.info(f"Processing {idx}/{total}: {file_path.name}")
                    
                    # Send to N8N for transcription
                    # Note: N8N model should handle media files differently from text
                    success, transcript, error = self.n8n_model.transcribe_media(
                        file_path=str(file_path)
                    )
                    
                    if success and transcript:
                        # Create output subfolder structure if recursive
                        if recursive:
                            relative_path = file_path.parent.relative_to(Path(source_folder))
                            current_output_folder = output_path / relative_path
                            current_output_folder.mkdir(parents=True, exist_ok=True)
                            logger.debug(f"Created output subfolder: {current_output_folder}")
                        else:
                            current_output_folder = output_path
                        
                        # Save transcript in selected formats
                        self._save_transcript(current_output_folder, file_path, transcript, output_formats)
                        
                        # Log success
                        self.view.root.after(
                            0,
                            self.view.append_log,
                            f"{file_path.name} - Transcribed successfully",
                            "success"
                        )
                        successful += 1
                        logger.info(f"Successfully transcribed {file_path.name}")
                    else:
                        # N8N returned error
                        error_msg = error or "Unknown error from N8N"
                        raise Exception(error_msg)
                
                except Exception as e:
                    # File processing failed - log and continue
                    error_msg = str(e)[:60]  # Truncate long errors
                    logger.error(f"Error transcribing {file_path.name}: {str(e)}")
                    
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
    
    def _create_output_folder(self, source_folder: str, output_location: str) -> Path:
        """
        Create output folder structure.
        
        If output_location is default (parent folder), creates:
        "[SourceFolderName] - Transcribed"
        
        If custom location, uses that directly.
        
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
                # Create subfolder with original name + "- Transcribed"
                output_path = output_path / f"{source_folder_name} - Transcribed"
                logger.info(f"Using default output location: {source_folder_name} - Transcribed")
            
            output_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output folder: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error creating output folder: {str(e)}")
            raise
    
    def _save_transcript(self, output_folder: Path, source_file: Path, 
                        transcript: str, output_formats: Dict) -> None:
        """
        Save transcript in selected formats.
        
        Supports: SRT, TXT, VTT, JSON
        
        Args:
            output_folder: Path to output folder
            source_file: Path to source media file
            transcript: Transcript text or data from N8N
            output_formats: Dict with format flags {'srt': bool, 'txt': bool, 'vtt': bool, 'json': bool}
        """
        try:
            base_name = source_file.stem
            
            # SRT format
            if output_formats.get('srt'):
                output_path = output_folder / f"{base_name}.srt"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(transcript if isinstance(transcript, str) else str(transcript))
                logger.info(f"Saved SRT transcript: {output_path}")
            
            # TXT format (plain text)
            if output_formats.get('txt'):
                output_path = output_folder / f"{base_name}.txt"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(transcript if isinstance(transcript, str) else str(transcript))
                logger.info(f"Saved TXT transcript: {output_path}")
            
            # VTT format (WebVTT)
            if output_formats.get('vtt'):
                output_path = output_folder / f"{base_name}.vtt"
                with open(output_path, "w", encoding="utf-8") as f:
                    # VTT header
                    f.write("WEBVTT\n\n")
                    f.write(transcript if isinstance(transcript, str) else str(transcript))
                logger.info(f"Saved VTT transcript: {output_path}")
            
            # JSON format
            if output_formats.get('json'):
                import json
                output_path = output_folder / f"{base_name}.json"
                
                # Create JSON structure
                json_data = {
                    "source_file": source_file.name,
                    "created_at": datetime.now().isoformat(),
                    "transcript": transcript if isinstance(transcript, str) else str(transcript)
                }
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved JSON transcript: {output_path}")
        
        except Exception as e:
            logger.error(f"Error saving transcript for {source_file.name}: {str(e)}")
            raise
    
    # Completion Handling
    
    def _show_completion_summary(self, total: int, successful: int, failed: int, 
                                 failed_files: List[str]):
        """
        Show processing completion summary.
        
        Called after background thread finishes.
        
        Args:
            total: Total files processed
            successful: Files successfully transcribed
            failed: Files that failed
            failed_files: List of failed file names
        """
        # Re-enable processing buttons
        self.view.set_processing_enabled(True)
        self.is_processing = False
        
        # Log summary
        self.view.append_log("=" * 50, "info")
        self.view.append_log(f"Transcription Complete!", "success")
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
        logger.info(f"Bulk transcription complete: {successful}/{total} successful, {failed} failed")
        if failed > 0:
            logger.warning(f"Failed files: {failed_files}")

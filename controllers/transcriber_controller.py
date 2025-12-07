"""
Transcriber Controller v3.1.2 - Transcript storage & tab integration

Responsibilities:
    - Listen to Transcriber tab UI events
    - Call TranscribeModel to transcribe files/URLs
    - Handle output location and format selection
    - Store transcript in memory (NEW v3.1.2)
    - Export individual file formats
    - Update view with results
    - Handle errors and status messages
    - Cleanup temporary files

New in v3.1.2:
    - Store transcript in memory (persist for session)
    - Enables export even if temp files deleted
    - Allows sharing transcript with other controllers

Connects:
    - TranscriberTab (view)
    - TranscribeModel (business logic)

Reusable by:
    - TranscriberTab (primary)
    - FileTab (secondary - transcribe first, then summarize)
    - YouTubeSummarizerTab (receives forwarded transcripts)
    - Other tabs (future)

Created: 2025-12-07 (v2.3)
Enhanced: 2025-12-07 (v2.4 - Output options)
Improved: 2025-12-07 (v3.1.2 - In-memory storage)
Version: 3.1.2
"""
from models.transcribe_model import TranscribeModel
from models.n8n_model import N8NModel
from utils.logger import logger
from pathlib import Path
import threading
import os
import shutil
import tempfile


class TranscriberController:
    """
    Coordinates Transcriber tab UI and transcription model.
    
    Responsibilities:
    - Transcribe local files or YouTube URLs
    - Manage output location (original vs custom)
    - Handle user-selected file formats
    - Store transcript in memory (NEW v3.1.2)
    - Export individual formats
    - Cleanup temporary files
    """
    
    def __init__(self, view):
        """
        Initialize Transcriber controller.
        
        Args:
            view: TranscriberTab instance
        """
        self.view = view
        self.transcribe_model = TranscribeModel()
        self.n8n_model = N8NModel()
        self.last_transcript_path = None  # Store last export location
        
        # In-memory storage (NEW v3.1.2 - persist for session)
        self.current_transcript = None  # Transcript content in memory
        self.current_transcript_format = None  # Format (.txt, .srt, etc.)
        
        # Wire up view callbacks
        self.view.on_file_selected = self._handle_file_selected
        self.view.on_transcribe_clicked = self._handle_transcribe_clicked
        self.view.on_copy_clicked = self._handle_copy_clicked
        self.view.on_export_txt_clicked = self._handle_export_txt_clicked
        self.view.on_export_srt_clicked = self._handle_export_srt_clicked
        self.view.on_clear_clicked = self._handle_clear_clicked
        
        logger.info("TranscriberController initialized (v3.1.2)")
    
    def set_transcript_from_youtube(self, transcript_content: str, format_ext: str):
        """
        Set transcript received from YouTube Summarizer tab.
        NEW in v3.1.2
        
        Args:
            transcript_content: Transcript text
            format_ext: Format (.txt, .srt, etc.)
        """
        self.current_transcript = transcript_content
        self.current_transcript_format = format_ext
        logger.info(f"Transcript received from YouTube tab ({format_ext}, {len(transcript_content)} chars)")
    
    def _handle_file_selected(self, file_path: str):
        """
        Handle file selection.
        
        Args:
            file_path: Path to selected file
        """
        logger.info(f"File selected: {file_path}")
        self.view.set_status(f"Ready to transcribe: {Path(file_path).name}")
    
    def _handle_transcribe_clicked(self):
        """
        Handle Transcribe button click.
        
        Transcribes based on current mode (local file or YouTube URL)
        """
        mode = self.view.get_mode()
        device = self.view.get_device()
        
        if mode == "local":
            self._transcribe_local_file(device)
        else:
            self._transcribe_youtube_url(device)
    
    def _get_output_directory(self, default_dir: Path = None) -> Path:
        """
        Get output directory based on user selection.
        
        Args:
            default_dir: Default directory if original location selected
        
        Returns:
            Path to output directory
        """
        location = self.view.get_output_location()
        
        if location == "custom":
            custom_path = self.view.get_output_path()
            if custom_path:
                return Path(custom_path)
            else:
                self.view.show_error("Please select a custom output directory")
                return None
        else:
            # Original location
            if default_dir:
                return default_dir
            else:
                # For YouTube without specified dir, use Documents
                return Path.home() / "Documents" / "Transcribe Anything"
    
    def _transcribe_local_file(self, device: str):
        """
        Transcribe a local file.
        
        Args:
            device: Device to use (cpu, cuda, insane, mps)
        """
        file_path = self.view.get_file_path()
        
        if not file_path or not file_path.strip():
            self.view.show_error("Please select a file first")
            return
        
        # Get output directory
        output_dir = self._get_output_directory(Path(file_path).parent)
        if not output_dir:
            return
        
        # Show loading state
        self.view.set_status(f"Transcribing: {Path(file_path).name}...")
        self.view.show_loading(True)
        
        # Run in background thread
        thread = threading.Thread(
            target=self._transcribe_file_background,
            args=(file_path, device, output_dir),
            daemon=True
        )
        thread.start()
    
    def _transcribe_file_background(self, file_path: str, device: str, output_dir: Path):
        """
        Background thread for file transcription.
        
        Args:
            file_path: Path to local file
            device: Device to use
            output_dir: Output directory
        """
        try:
            logger.info(f"Starting transcription: {file_path}")
            
            # Get user-selected formats
            keep_formats = self.view.get_keep_formats()
            if not keep_formats:
                self.view.show_error("Please select at least one output format")
                return
            
            success, srt_content, error, metadata = self.transcribe_model.transcribe_file(
                file_path=file_path,
                device=device,
                output_dir=str(output_dir),
                keep_formats=keep_formats
            )
            
            if success and srt_content:
                # Store transcript in memory (NEW v3.1.2)
                self.current_transcript = srt_content
                self.current_transcript_format = keep_formats[0] if keep_formats else '.txt'
                
                # Store last transcript path for exports
                self.last_transcript_path = metadata.get('output_dir')
                
                # Display transcript
                self.view.set_transcript(srt_content)
                self.view.set_status(
                    f"✓ Transcribed: {metadata.get('base_name', 'Unknown')}\n"
                    f"Files: {', '.join(metadata.get('files_kept', []))}\n"
                    f"Location: {metadata.get('output_dir', 'N/A')}"
                )
                self.view.show_success(f"Transcription complete!\nSaved to: {metadata.get('output_dir')}")
                logger.info(f"Transcription successful: {file_path}")
            else:
                self.view.show_error(f"Transcription failed: {error}")
                logger.error(f"Transcription failed: {error}")
        
        except Exception as e:
            error_msg = f"Error during transcription: {str(e)}"
            self.view.show_error(error_msg)
            logger.error(error_msg, exc_info=True)
        
        finally:
            self.view.show_loading(False)
            self._cleanup_temp_files()
    
    def _transcribe_youtube_url(self, device: str):
        """
        Transcribe a YouTube URL.
        
        Args:
            device: Device to use (cpu, cuda, insane, mps)
        """
        url = self.view.get_youtube_url()
        
        if not url or not url.strip():
            self.view.show_error("Please enter a YouTube URL")
            return
        
        if not self.transcribe_model.validate_youtube_url(url):
            self.view.show_error("Invalid YouTube URL. Please provide a valid YouTube link.")
            return
        
        # Show loading state
        self.view.set_status(f"Transcribing YouTube video...")
        self.view.show_loading(True)
        
        # Run in background thread
        thread = threading.Thread(
            target=self._transcribe_youtube_background,
            args=(url, device),
            daemon=True
        )
        thread.start()
    
    def _transcribe_youtube_background(self, url: str, device: str):
        """
        Background thread for YouTube transcription.
        
        Args:
            url: YouTube URL
            device: Device to use
        """
        try:
            logger.info(f"Starting YouTube transcription: {url}")
            
            # Get user-selected formats
            keep_formats = self.view.get_keep_formats()
            if not keep_formats:
                self.view.show_error("Please select at least one output format")
                return
            
            # Get output directory
            output_dir = self._get_output_directory()
            if not output_dir:
                return
            
            success, srt_content, error, metadata = self.transcribe_model.transcribe_youtube(
                youtube_url=url,
                device=device,
                output_dir=str(output_dir),
                keep_formats=keep_formats
            )
            
            if success and srt_content:
                # Store transcript in memory (NEW v3.1.2)
                self.current_transcript = srt_content
                self.current_transcript_format = keep_formats[0] if keep_formats else '.txt'
                
                # Store last transcript path for exports
                self.last_transcript_path = metadata.get('output_dir')
                
                # Display transcript
                self.view.set_transcript(srt_content)
                self.view.set_status(
                    f"✓ Transcribed: {metadata.get('base_name', 'Unknown')}\n"
                    f"Files: {', '.join(metadata.get('files_kept', []))}\n"
                    f"Location: {metadata.get('output_dir', 'N/A')}"
                )
                self.view.show_success(f"YouTube transcription complete!\nSaved to: {metadata.get('output_dir')}")
                logger.info(f"YouTube transcription successful: {url}")
            else:
                self.view.show_error(f"Transcription failed: {error}")
                logger.error(f"YouTube transcription failed: {error}")
        
        except Exception as e:
            error_msg = f"Error during YouTube transcription: {str(e)}"
            self.view.show_error(error_msg)
            logger.error(error_msg, exc_info=True)
        
        finally:
            self.view.show_loading(False)
            self._cleanup_temp_files()
    
    def _handle_copy_clicked(self):
        """
        Handle Copy to Clipboard button click.
        """
        if self.view.copy_to_clipboard():
            logger.info("Transcript copied to clipboard")
        else:
            logger.warning("Failed to copy transcript")
    
    def _handle_export_txt_clicked(self):
        """
        Handle Export .txt button click.
        Uses in-memory transcript if available (NEW v3.1.2)
        """
        # Check in-memory transcript FIRST (NEW v3.1.2)
        if self.current_transcript:
            try:
                from tkinter import filedialog
                filename = f"transcript_{self.current_transcript_format}.txt"
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    initialfile=filename,
                    filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
                )
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.current_transcript)
                    self.view.show_success(f"Transcript exported to: {file_path}")
                    logger.info(f"Transcript exported: {file_path}")
            except Exception as e:
                self.view.show_error(f"Failed to export: {str(e)}")
                logger.error(f"Export failed: {str(e)}", exc_info=True)
        elif self.last_transcript_path:
            try:
                transcript_path = Path(self.last_transcript_path)
                # Find .txt file in the directory
                txt_files = list(transcript_path.glob("*.txt"))
                if not txt_files:
                    self.view.show_error("No .txt file found. Check output formats.")
                    return
                
                # Open directory containing the file
                import subprocess
                import sys
                if os.name == 'nt':  # Windows
                    os.startfile(transcript_path)
                else:  # Linux/Mac
                    subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(transcript_path)])
                
                self.view.show_success(f"Opened: {transcript_path}")
            except Exception as e:
                self.view.show_error(f"Failed to export .txt: {str(e)}")
                logger.error(f"Export .txt failed: {str(e)}", exc_info=True)
        else:
            self.view.show_error("No transcript to export. Transcribe first.")
    
    def _handle_export_srt_clicked(self):
        """
        Handle Export .srt button click.
        Uses in-memory transcript if available (NEW v3.1.2)
        """
        # Check in-memory transcript FIRST (NEW v3.1.2)
        if self.current_transcript:
            try:
                from tkinter import filedialog
                filename = f"transcript_{self.current_transcript_format}.srt"
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".srt",
                    initialfile=filename,
                    filetypes=[("SRT Files", "*.srt"), ("All Files", "*.*")]
                )
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.current_transcript)
                    self.view.show_success(f"Transcript exported to: {file_path}")
                    logger.info(f"Transcript exported: {file_path}")
            except Exception as e:
                self.view.show_error(f"Failed to export: {str(e)}")
                logger.error(f"Export failed: {str(e)}", exc_info=True)
        elif self.last_transcript_path:
            try:
                transcript_path = Path(self.last_transcript_path)
                # Find .srt file in the directory
                srt_files = list(transcript_path.glob("*.srt"))
                if not srt_files:
                    self.view.show_error("No .srt file found. Check output formats.")
                    return
                
                # Open directory containing the file
                import subprocess
                import sys
                if os.name == 'nt':  # Windows
                    os.startfile(transcript_path)
                else:  # Linux/Mac
                    subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(transcript_path)])
                
                self.view.show_success(f"Opened: {transcript_path}")
            except Exception as e:
                self.view.show_error(f"Failed to export .srt: {str(e)}")
                logger.error(f"Export .srt failed: {str(e)}", exc_info=True)
        else:
            self.view.show_error("No transcript to export. Transcribe first.")
    
    def _handle_clear_clicked(self):
        """
        Handle Clear button click.
        """
        self.view.clear_all()
        # Clear in-memory transcript (NEW v3.1.2)
        self.current_transcript = None
        self.current_transcript_format = None
        logger.info("Transcriber tab cleared")
    
    def _cleanup_temp_files(self):
        """
        Cleanup temporary files created during transcription.
        """
        try:
            # Clean up system temp directory
            temp_dir = tempfile.gettempdir()
            # Look for transcribe-anything temp files and remove them
            for item in Path(temp_dir).iterdir():
                if 'transcribe' in str(item).lower():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        logger.info(f"Cleaned up temp file: {item}")
                    except Exception as e:
                        logger.warning(f"Could not clean up {item}: {str(e)}")
        except Exception as e:
            logger.warning(f"Temp cleanup error: {str(e)}")
    
    # Public methods for use by other controllers/tabs
    
    def get_transcript(self) -> str:
        """
        Get current transcript (for use by other tabs).
        
        Returns:
            str: SRT transcript content
        """
        return self.view.get_transcript()
    
    def transcribe_file_for_tab(
        self,
        file_path: str,
        device: str = "cuda",
        keep_formats: list = None
    ) -> tuple:
        """
        Transcribe file for use by other tabs (like FileTab).
        
        Args:
            file_path: Path to media file
            device: Device to use
            keep_formats: Formats to keep (default: ['.txt', '.srt'])
        
        Returns:
            Tuple: (success, transcript_content, error_msg, metadata)
        """
        if keep_formats is None:
            keep_formats = ['.txt', '.srt']
        
        logger.info(f"Transcribing file for tab: {file_path}")
        return self.transcribe_model.transcribe_file(
            file_path=file_path,
            device=device,
            keep_formats=keep_formats
        )
    
    def transcribe_youtube_for_tab(
        self,
        youtube_url: str,
        device: str = "cuda",
        keep_formats: list = None
    ) -> tuple:
        """
        Transcribe YouTube URL for use by other tabs.
        
        Args:
            youtube_url: YouTube video URL
            device: Device to use
            keep_formats: Formats to keep (default: ['.txt', '.srt'])
        
        Returns:
            Tuple: (success, transcript_content, error_msg, metadata)
        """
        if keep_formats is None:
            keep_formats = ['.txt', '.srt']
        
        logger.info(f"Transcribing YouTube for tab: {youtube_url}")
        return self.transcribe_model.transcribe_youtube(
            youtube_url=youtube_url,
            device=device,
            keep_formats=keep_formats
        )

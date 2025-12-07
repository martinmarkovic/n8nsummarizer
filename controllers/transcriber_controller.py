"""
Transcriber Controller - Coordinates transcription UI and model

Responsibilities:
    - Listen to Transcriber tab UI events
    - Call TranscribeModel to transcribe files/URLs
    - Update view with results
    - Handle errors and status messages
    - Manage output files (SRT, TXT)

Connects:
    - TranscriberTab (view)
    - TranscribeModel (business logic)

Reusable by:
    - TranscriberTab (primary)
    - FileTab (secondary - transcribe first, then summarize)
    - Other tabs (future)

Created: 2025-12-07 (v2.3)
Version: 2.3
"""
from models.transcribe_model import TranscribeModel
from models.n8n_model import N8NModel
from utils.logger import logger
from pathlib import Path
import threading


class TranscriberController:
    """
    Coordinates Transcriber tab UI and transcription model.
    
    Responsibilities:
    - Transcribe local files or YouTube URLs
    - Manage output files (SRT, TXT by default)
    - Handle device selection
    - Update UI with results
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
        
        # Wire up view callbacks
        self.view.on_file_selected = self._handle_file_selected
        self.view.on_transcribe_clicked = self._handle_transcribe_clicked
        self.view.on_copy_clicked = self._handle_copy_clicked
        self.view.on_clear_clicked = self._handle_clear_clicked
        
        logger.info("TranscriberController initialized")
    
    def _handle_file_selected(self, file_path: str):
        """
        Handle file selection.
        
        Args:
            file_path: Path to selected file
        """
        logger.info(f"File selected: {file_path}")
        # Just confirm selection - transcription happens on button click
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
        
        # Show loading state
        self.view.set_status(f"Transcribing: {Path(file_path).name}...")
        self.view.show_loading(True)
        
        # Run in background thread to avoid blocking UI
        thread = threading.Thread(
            target=self._transcribe_file_background,
            args=(file_path, device),
            daemon=True
        )
        thread.start()
    
    def _transcribe_file_background(self, file_path: str, device: str):
        """
        Background thread for file transcription.
        
        Args:
            file_path: Path to local file
            device: Device to use
        """
        try:
            logger.info(f"Starting transcription: {file_path}")
            
            success, srt_content, error, metadata = self.transcribe_model.transcribe_file(
                file_path=file_path,
                device=device,
                keep_formats=['.txt', '.srt']  # Only keep txt and srt
            )
            
            if success and srt_content:
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
            
            success, srt_content, error, metadata = self.transcribe_model.transcribe_youtube(
                youtube_url=url,
                device=device,
                keep_formats=['.txt', '.srt']  # Only keep txt and srt
            )
            
            if success and srt_content:
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
    
    def _handle_copy_clicked(self):
        """
        Handle Copy to Clipboard button click.
        """
        if self.view.copy_to_clipboard():
            logger.info("Transcript copied to clipboard")
        else:
            logger.warning("Failed to copy transcript")
    
    def _handle_clear_clicked(self):
        """
        Handle Clear button click.
        """
        self.view.clear_all()
        logger.info("Transcriber tab cleared")
    
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
        device: str = "cuda"
    ) -> tuple:
        """
        Transcribe file for use by other tabs (like FileTab).
        
        This allows FileTab to transcribe a file, then summarize the transcript.
        
        Args:
            file_path: Path to media file
            device: Device to use
        
        Returns:
            Tuple: (success, transcript_content, error_msg, metadata)
        """
        logger.info(f"Transcribing file for tab: {file_path}")
        return self.transcribe_model.transcribe_file(
            file_path=file_path,
            device=device,
            keep_formats=['.txt', '.srt']
        )
    
    def transcribe_youtube_for_tab(
        self,
        youtube_url: str,
        device: str = "cuda"
    ) -> tuple:
        """
        Transcribe YouTube URL for use by other tabs.
        
        Args:
            youtube_url: YouTube video URL
            device: Device to use
        
        Returns:
            Tuple: (success, transcript_content, error_msg, metadata)
        """
        logger.info(f"Transcribing YouTube for tab: {youtube_url}")
        return self.transcribe_model.transcribe_youtube(
            youtube_url=youtube_url,
            device=device,
            keep_formats=['.txt', '.srt']
        )

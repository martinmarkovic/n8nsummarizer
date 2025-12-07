"""
YouTube Summarizer Controller v3.0 - Coordinates YouTube tab + models

Responsibilities:
    - Listen to YouTubeSummarizerTab UI events
    - Validate YouTube URLs
    - Call TranscribeModel for YouTube transcription
    - Call N8NModel for summarization
    - Handle file operations (export txt, srt, clipboard)
    - Manage threading for blocking operations
    - Error handling and user feedback

Controller is THIN - just coordinates, doesn't contain business logic.

Version: 3.0
Created: 2025-12-07
"""
import os
import threading
import pyperclip
from datetime import datetime
from tkinter import filedialog
from models.transcribe_model import TranscribeModel
from models.n8n_model import N8NModel
from utils.logger import logger
from config import EXPORT_DIR


class YouTubeSummarizerController:
    """
    Coordinates YouTube Summarizer tab UI and models.
    
    Flow:
    1. User enters YouTube URL
    2. Controller validates URL
    3. Calls TranscribeModel to transcribe YouTube video
    4. Saves transcript to disk
    5. Sends transcript to N8NModel for summarization
    6. N8NModel calls n8n webhook
    7. Displays summary in UI
    8. User can export or copy
    """
    
    def __init__(self, view):
        """
        Initialize controller with view reference.
        
        Args:
            view: YouTubeSummarizerTab instance
        """
        self.view = view
        self.transcribe_model = TranscribeModel()
        self.n8n_model = N8NModel()
        
        # Wire up view callbacks
        self.view.on_transcribe_clicked = self.handle_transcribe_clicked
        self.view.on_export_txt_clicked = self.handle_export_txt
        self.view.on_export_srt_clicked = self.handle_export_srt
        self.view.on_copy_clipboard_clicked = self.handle_copy_clipboard
        
        # State tracking
        self.current_summary = None
        self.current_youtube_title = None
        
        logger.info("YouTubeSummarizerController initialized (v3.0)")
    
    def handle_transcribe_clicked(self):
        """
        Handle Transcribe button - starts background thread.
        """
        logger.info("Transcribe button clicked")
        
        # Get and validate URL
        youtube_url = self.view.get_youtube_url()
        if not youtube_url or youtube_url == "https://":
            self.view.show_error("Please enter a YouTube URL")
            return
        
        # Validate YouTube URL format
        if not TranscribeModel.validate_youtube_url(youtube_url):
            self.view.show_error(
                "Invalid YouTube URL.\n\n"
                "Supported formats:\n"
                "- https://youtube.com/watch?v=...\n"
                "- https://youtu.be/...\n"
                "- https://youtube.com/embed/..."
            )
            return
        
        # Get selected format
        format_ext = self.view.get_transcription_format()
        keep_formats = [format_ext]
        
        # Update UI
        self.view.set_input_status("Transcribing YouTube video...", "blue")
        self.view.set_transcribe_button_enabled(False)
        self.view.set_export_buttons_enabled(False)
        self.view.set_summary_content("Transcribing YouTube video...\nThis may take a few minutes depending on video length.")
        
        # Start background thread
        thread = threading.Thread(
            target=self._transcribe_youtube_thread,
            args=(youtube_url, keep_formats),
            daemon=True
        )
        thread.start()
    
    def _transcribe_youtube_thread(self, youtube_url: str, keep_formats: list):
        """
        Background thread for YouTube transcription.
        
        Args:
            youtube_url: YouTube video URL
            keep_formats: File formats to keep
        """
        try:
            logger.info(f"Starting YouTube transcription: {youtube_url}")
            
            # Transcribe YouTube video
            success, transcript_content, error, metadata = self.transcribe_model.transcribe_youtube(
                youtube_url=youtube_url,
                device="cuda",
                keep_formats=keep_formats
            )
            
            if not success:
                error_msg = error or "Unknown error during transcription"
                self.view.root.after(0, self._on_transcribe_error, error_msg)
                return
            
            if not transcript_content:
                self.view.root.after(
                    0,
                    self._on_transcribe_error,
                    "No transcript generated from YouTube video"
                )
                return
            
            logger.info(f"Transcription successful: {len(transcript_content)} characters")
            
            # Store metadata
            self.current_youtube_title = metadata.get('base_name', 'youtube_video') if metadata else 'youtube_video'
            
            # Send to n8n for summarization
            self.view.root.after(
                0,
                self._on_transcribe_success,
                transcript_content,
                metadata
            )
        
        except Exception as e:
            error_msg = f"Unexpected error during transcription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.view.root.after(0, self._on_transcribe_error, error_msg)
    
    def _on_transcribe_success(self, transcript_content: str, metadata: dict):
        """
        Handle successful transcription - proceed to summarization.
        
        Args:
            transcript_content: Transcript text
            metadata: Transcription metadata
        """
        logger.info("Transcription succeeded, sending to n8n for summarization...")
        
        self.view.set_input_status("Sending to n8n for summarization...", "blue")
        self.view.set_summary_content(
            f"Transcript received ({len(transcript_content)} characters)\n\n"
            f"Sending to n8n for summarization...\n\n"
            f"Please wait..."
        )
        
        # Start background thread for n8n summarization
        thread = threading.Thread(
            target=self._summarize_with_n8n_thread,
            args=(transcript_content, metadata),
            daemon=True
        )
        thread.start()
    
    def _on_transcribe_error(self, error_msg: str):
        """
        Handle transcription error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Transcription error: {error_msg}")
        self.view.show_error(f"Transcription failed:\n\n{error_msg}")
        self.view.set_input_status("Transcription failed", "red")
        self.view.set_transcribe_button_enabled(True)
        self.view.set_summary_content(
            f"Error during transcription:\n\n{error_msg}\n\n"
            f"Please try again."
        )
    
    def _summarize_with_n8n_thread(self, transcript_content: str, metadata: dict):
        """
        Background thread for n8n summarization.
        
        Args:
            transcript_content: Transcript text to summarize
            metadata: Metadata about transcript
        """
        try:
            logger.info("Sending transcript to n8n webhook...")
            
            # Send to n8n
            success, response_data, error = self.n8n_model.send_content(
                file_name=self.current_youtube_title or 'youtube_video',
                content=transcript_content,
                metadata={
                    'source': 'youtube',
                    'transcript_length': len(transcript_content)
                }
            )
            
            if not success:
                error_msg = error or "Unknown error from n8n"
                self.view.root.after(0, self._on_n8n_error, error_msg)
                return
            
            # Extract summary from response
            summary = self.n8n_model.extract_summary(response_data)
            
            if not summary:
                self.view.root.after(
                    0,
                    self._on_n8n_error,
                    "No summary returned from n8n"
                )
                return
            
            logger.info(f"Summary received: {len(summary)} characters")
            self.current_summary = summary
            
            # Display summary
            self.view.root.after(0, self._on_n8n_success, summary)
        
        except Exception as e:
            error_msg = f"Unexpected error during summarization: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.view.root.after(0, self._on_n8n_error, error_msg)
    
    def _on_n8n_success(self, summary: str):
        """
        Handle successful summarization.
        
        Args:
            summary: Summary text from n8n
        """
        logger.info("Summarization succeeded")
        
        self.view.set_summary_content(summary)
        self.view.set_input_status("Summarization complete!", "green")
        self.view.set_output_status("Summary ready. You can now export or copy.", "green")
        self.view.set_export_buttons_enabled(True)
        self.view.set_transcribe_button_enabled(True)
        self.view.show_success("YouTube video transcribed and summarized successfully!")
    
    def _on_n8n_error(self, error_msg: str):
        """
        Handle n8n summarization error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"n8n summarization error: {error_msg}")
        self.view.show_error(f"Summarization failed:\n\n{error_msg}")
        self.view.set_input_status("Summarization failed", "red")
        self.view.set_output_status(f"Error: {error_msg}", "red")
        self.view.set_transcribe_button_enabled(True)
    
    def handle_export_txt(self):
        """
        Export summary as .txt file.
        """
        if not self.current_summary:
            self.view.show_error("No summary to export. Please transcribe a YouTube video first.")
            return
        
        # Determine filename
        default_filename = f"{self.current_youtube_title or 'youtube_summary'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Show file dialog
        file_path = filedialog.asksaveasfilename(
            title="Export Summary as .txt",
            defaultextension=".txt",
            initialdir=EXPORT_DIR,
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.current_summary)
            
            logger.info(f"Summary exported to: {file_path}")
            self.view.show_success(f"Summary exported successfully to:\n{file_path}")
            self.view.set_output_status(f"Exported to {os.path.basename(file_path)}", "green")
        
        except Exception as e:
            error_msg = f"Failed to export file: {str(e)}"
            logger.error(error_msg)
            self.view.show_error(error_msg)
    
    def handle_export_srt(self):
        """
        Export summary as .srt file (caption format).
        
        Converts summary text into SRT subtitle format:
        - Splits by sentences/paragraphs
        - Adds timing (00:00:00,000 --> 00:00:05,000)
        - Saves as .srt file
        """
        if not self.current_summary:
            self.view.show_error("No summary to export. Please transcribe a YouTube video first.")
            return
        
        # Determine filename
        default_filename = f"{self.current_youtube_title or 'youtube_summary'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt"
        
        # Show file dialog
        file_path = filedialog.asksaveasfilename(
            title="Export Summary as .srt",
            defaultextension=".srt",
            initialdir=EXPORT_DIR,
            initialfile=default_filename,
            filetypes=[("SRT Subtitle Files", "*.srt"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Convert summary to SRT format
            srt_content = self._convert_summary_to_srt(self.current_summary)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"Summary exported as SRT to: {file_path}")
            self.view.show_success(f"Summary exported successfully as .srt to:\n{file_path}")
            self.view.set_output_status(f"Exported to {os.path.basename(file_path)}", "green")
        
        except Exception as e:
            error_msg = f"Failed to export SRT file: {str(e)}"
            logger.error(error_msg)
            self.view.show_error(error_msg)
    
    def _convert_summary_to_srt(self, summary: str) -> str:
        """
        Convert summary text to SRT subtitle format.
        
        Args:
            summary: Summary text
        
        Returns:
            SRT formatted text
        """
        import re
        
        # Split by sentences (periods, question marks, exclamation marks)
        sentences = re.split(r'(?<=[.!?])\s+', summary.strip())
        
        srt_lines = []
        subtitle_number = 1
        seconds_per_subtitle = 5  # Each subtitle lasts 5 seconds
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            # Calculate timing
            start_seconds = i * seconds_per_subtitle
            end_seconds = (i + 1) * seconds_per_subtitle
            
            start_time = self._format_srt_time(start_seconds)
            end_time = self._format_srt_time(end_seconds)
            
            # Build SRT entry
            srt_lines.append(str(subtitle_number))
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(sentence.strip())
            srt_lines.append("")  # Empty line between entries
            
            subtitle_number += 1
        
        return "\n".join(srt_lines)
    
    @staticmethod
    def _format_srt_time(seconds: int) -> str:
        """
        Format seconds to SRT time format (HH:MM:SS,mmm).
        
        Args:
            seconds: Number of seconds
        
        Returns:
            SRT time string
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        millis = 0
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},000"
    
    def handle_copy_clipboard(self):
        """
        Copy summary to clipboard.
        """
        if not self.current_summary:
            self.view.show_error("No summary to copy. Please transcribe a YouTube video first.")
            return
        
        try:
            pyperclip.copy(self.current_summary)
            logger.info("Summary copied to clipboard")
            self.view.show_success(f"Summary copied to clipboard ({len(self.current_summary)} characters)")
            self.view.set_output_status("Copied to clipboard", "green")
        
        except Exception as e:
            error_msg = f"Failed to copy to clipboard: {str(e)}"
            logger.error(error_msg)
            self.view.show_error(error_msg)

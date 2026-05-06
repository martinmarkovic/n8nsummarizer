"""
Summarizer Controller - Unified File and YouTube Summarization Controller

Replaces FileController and YouTubeSummarizerController with a single controller
that coordinates SummarizerTab with FileModel, LLMClient, and TranscribeModel.

This controller is THIN - it coordinates workflows but contains no business logic.
All business logic resides in the models.

Version: 1.0
Created: 2026-05-06
"""

import os
import threading
from tkinter import filedialog
from typing import Optional, Dict, Any

from models.file_model import FileModel
from models.llm_client import LLMClient
from models.transcribe_model import TranscribeModel
from utils.logger import logger
from config import EXPORT_DIR

# Try to import pyperclip for better clipboard support
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    logger.warning("pyperclip not installed. Using tkinter clipboard fallback.")


class SummarizerController:
    """
    Unified summarizer controller that replaces FileController and YouTubeSummarizerController.
    
    Coordinates SummarizerTab with FileModel, LLMClient, and TranscribeModel to provide
    direct LLM-based summarization for both file and YouTube inputs.
    """
    
    def __init__(
        self,
        view,
        transcriber_tab=None,
        transcriber_controller=None
    ):
        """
        Initialize SummarizerController.
        
        Args:
            view: SummarizerTab instance
            transcriber_tab: Optional TranscriberTab instance for forwarding
            transcriber_controller: Optional TranscriberController instance
        """
        self.view = view
        self.transcriber_tab = transcriber_tab
        self.transcriber_controller = transcriber_controller
        
        # Initialize models
        self.file_model = FileModel()
        self.llm_client = LLMClient()
        self.transcribe_model = TranscribeModel()
        
        # State tracking
        self.current_summary = None
        self.current_transcript = None
        self.current_youtube_title = None
        self.current_metadata = None
        
        # Wire up view callbacks
        self.view.on_file_selected = self.handle_file_selected
        self.view.on_send_clicked = self.handle_send_clicked
        self.view.on_export_txt = self.handle_export_txt
        self.view.on_export_docx = self.handle_export_docx
        self.view.on_copy_clicked = self.handle_copy_clicked
        # Note: on_clear_clicked is optional - view has default clear_all()
        
        logger.info("SummarizerController initialized - unified file/YouTube summarization")
    
    def handle_file_selected(self, file_path: str):
        """Handle file selection from view."""
        # Use model to read file
        success, content, error = self.file_model.read_file(file_path)
        
        if success:
            self.view.set_file_path(file_path)
            self.view.set_content(content)
            
            # Get file info from model
            info = self.file_model.get_file_info(file_path)
            self.view.set_file_info(info)
            self.view.set_status(f"Loaded: {info['name']}")
        else:
            self.view.show_error(f"Failed to load file: {error}")
            self.view.set_file_path(None)
            self.view.set_content("")
            self.view.set_file_info(None)
    
    def handle_send_clicked(self):
        """Handle summarize button click - route to appropriate workflow."""
        mode = self.view.get_input_mode()
        
        if mode == "file":
            self._start_file_summarize()
        elif mode == "youtube":
            self._start_youtube_summarize()
        else:
            self.view.show_error(f"Unknown input mode: {mode}")
    
    def _update_llm_client(self) -> bool:
        """
        Update LLM client configuration from view settings.
        
        Returns:
            True if configuration updated successfully, False if validation failed
        """
        webhook_url = self.view.get_webhook_url()
        model_name = self.view.get_model_name()
        
        if not webhook_url:
            self.view.show_error("Webhook URL is empty. Please enter a valid URL.")
            return False
        
        # Update LLM client configuration
        self.llm_client.config.webhook_url = webhook_url
        self.llm_client.config.model_name = model_name
        
        # Save to .env if requested
        if self.view.get_save_settings():
            self.llm_client.save_settings_to_env(webhook_url, model_name)
        
        return True
    
    def _start_file_summarize(self):
        """Start file summarization workflow."""
        file_path = self.view.get_file_path()
        if not file_path:
            self.view.show_error("No file loaded. Please select a file first.")
            return
        
        content = self.view.get_content()
        if not content or not content.strip():
            self.view.show_error("File content is empty.")
            return
        
        if not self._update_llm_client():
            return
        
        prompt = self.view.get_prompt()
        
        # Update UI for processing
        self.view.set_status("Sending to LLM webhook...")
        self.view.display_response(
            f"Sending to {self.llm_client.config.webhook_url}...\n"
            f"Waiting for response..."
        )
        self.view.show_loading(True)
        
        # Start background thread
        thread = threading.Thread(
            target=self._summarize_file_thread,
            args=(file_path, content, prompt),
            daemon=True
        )
        thread.start()
    
    def _summarize_file_thread(self, file_path: str, content: str, prompt: str):
        """Background thread for file summarization."""
        try:
            # Get file info and size
            file_info = self.file_model.get_file_info(file_path)
            file_size_bytes = os.path.getsize(file_path)
            
            logger.info(f"Sending file to LLM: {file_info['name']} ({file_size_bytes} bytes)")
            
            # Send to LLM client
            success, summary, error = self.llm_client.send_content(
                file_name=file_info["name"],
                content=content,
                prompt=prompt,
                file_size_bytes=file_size_bytes
            )
            
            # Handle response on main thread
            if success:
                self.view.root.after(0, self._on_summarize_success, summary, file_info["name"])
            else:
                self.view.root.after(0, self._on_error, error or "Unknown error from LLM")
                
        except Exception as e:
            logger.error(f"File summarization error: {e}", exc_info=True)
            self.view.root.after(0, self._on_error, str(e))
    
    def _start_youtube_summarize(self):
        """Start YouTube transcription and summarization workflow."""
        youtube_url = self.view.get_youtube_url()
        if not youtube_url or youtube_url == "https://":
            self.view.show_error("Please enter a YouTube URL.")
            return
        
        if not TranscribeModel.validate_youtube_url(youtube_url):
            self.view.show_error("Invalid YouTube URL format.")
            return
        
        if not self._update_llm_client():
            return
        
        format_ext = self.view.get_transcription_format()
        prompt = self.view.get_prompt()
        
        # Update UI for transcription
        self.view.set_status("Transcribing YouTube video...")
        self.view.display_response(
            "Transcribing YouTube video...\n"
            "This may take a few minutes depending on video length."
        )
        self.view.show_loading(True)
        
        # Start transcription thread
        thread = threading.Thread(
            target=self._youtube_thread,
            args=(youtube_url, format_ext, prompt),
            daemon=True
        )
        thread.start()
    
    def _youtube_thread(self, youtube_url: str, format_ext: str, prompt: str):
        """Background thread for YouTube transcription."""
        try:
            logger.info(f"Transcribing YouTube video: {youtube_url}")
            
            # Transcribe YouTube video
            success, transcript_content, error, metadata = (
                self.transcribe_model.transcribe_youtube(
                    youtube_url=youtube_url,
                    device="cuda",
                    keep_formats=[format_ext]
                )
            )
            
            if not success or not transcript_content:
                error_msg = error or "No transcript generated"
                self.view.root.after(0, self._on_error, error_msg)
                return
            
            # Store transcript and metadata
            self.current_transcript = transcript_content
            self.current_youtube_title = (
                metadata.get("base_name", "youtube_video") 
                if metadata else "youtube_video"
            )
            self.current_metadata = metadata
            
            # Clean up temporary files
            self._cleanup_transcript_files()
            
            # Show transcript in UI
            self.view.root.after(0, self.view.set_content, transcript_content)
            self.view.root.after(0, self.view.display_response,
                f"Transcript loaded ({len(transcript_content)} characters)\n"
                f"Sending to LLM webhook..."
            )
            
            # Chain into summarization
            thread = threading.Thread(
                target=self._summarize_transcript_thread,
                args=(transcript_content, prompt),
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            logger.error(f"YouTube transcription error: {e}", exc_info=True)
            self.view.root.after(0, self._on_error, str(e))
    
    def _summarize_transcript_thread(self, transcript_content: str, prompt: str):
        """Background thread for transcript summarization."""
        try:
            file_name = (self.current_youtube_title or "transcript") + ".txt"
            
            logger.info(f"Summarizing transcript: {file_name} ({len(transcript_content)} chars)")
            
            # Send to LLM client
            success, summary, error = self.llm_client.send_content(
                file_name=file_name,
                content=transcript_content,
                prompt=prompt,
                file_size_bytes=len(transcript_content.encode("utf-8"))
            )
            
            # Handle response on main thread
            if success:
                self.view.root.after(0, self._on_summarize_success, summary, self.current_youtube_title)
                
                # Forward to transcriber if available
                if self.transcriber_controller and transcript_content:
                    self.view.root.after(0, self._forward_to_transcriber, transcript_content)
            else:
                self.view.root.after(0, self._on_error, error or "Unknown error from LLM")
                
        except Exception as e:
            logger.error(f"Transcript summarization error: {e}", exc_info=True)
            self.view.root.after(0, self._on_error, str(e))
    
    def _on_summarize_success(self, summary: str, display_name: str):
        """Handle successful summarization."""
        self.current_summary = summary
        self.view.display_response(summary)
        self.view.show_loading(False)
        self.view.set_export_buttons_enabled(True)
        self.view.set_status("Ready")
        
        # Handle auto-export preferences
        export_prefs = self.view.get_export_preferences()
        if export_prefs["auto_export_txt"]:
            self.handle_export_txt(manual_call=False)
        if export_prefs["auto_export_docx"]:
            self.handle_export_docx(manual_call=False)
        
        self.view.show_success(f"Summary complete for '{display_name}'")
    
    def _on_error(self, error_msg: str):
        """Handle errors."""
        self.view.display_response(f"Error:\n\n{error_msg}")
        self.view.show_error(f"Summarization failed:\n{error_msg}")
        self.view.show_loading(False)
        self.view.set_status("Ready")
    
    def _forward_to_transcriber(self, transcript_content: str):
        """Forward transcript to transcriber controller."""
        if hasattr(self.transcriber_controller, 'store_transcript'):
            try:
                self.transcriber_controller.store_transcript(
                    transcript_content,
                    self.current_youtube_title
                )
                logger.info("Transcript forwarded to transcriber controller")
            except Exception as e:
                logger.error(f"Failed to forward to transcriber: {e}")
                # Silently fail - not critical functionality
    
    def _cleanup_transcript_files(self):
        """Clean up temporary transcript files."""
        if not self.current_metadata:
            return
        
        temp_files = []
        if "temp_file" in self.current_metadata:
            temp_files.append(self.current_metadata["temp_file"])
        if "temp_files" in self.current_metadata:
            temp_files.extend(self.current_metadata["temp_files"])
        
        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Deleted temp file: {temp_file}")
                except Exception as e:
                    logger.error(f"Failed to delete temp file {temp_file}: {e}")
    
    def handle_export_txt(self, manual_call: bool = True):
        """Export summary as text file."""
        content = self.current_summary or self.view.get_response_content()
        if not content or not content.strip():
            if manual_call:
                self.view.show_error("No response content to export.")
            return
        
        export_prefs = self.view.get_export_preferences()
        
        # Determine filename based on mode and preferences
        if self.view.get_input_mode() == "file" and export_prefs["original_basename"]:
            filename = f"{export_prefs['original_basename']}_Summary.txt"
        elif self.current_youtube_title:
            filename = f"{self.current_youtube_title}_Summary.txt"
        else:
            filename = self.file_model.generate_timestamp_filename(format="txt")
        
        # Handle file location preferences
        file_path = None
        if export_prefs["use_original_location"] and export_prefs["original_directory"]:
            file_path = os.path.join(export_prefs["original_directory"], filename)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Failed to auto-export: {e}")
                file_path = None
        
        # If auto-export failed or not preferred, show save dialog
        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=filename,
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                self.view.show_error(f"Failed to export: {e}")
                return
        
        if manual_call:
            self.view.show_success(f"Exported to {file_path}")
    
    def handle_export_docx(self, manual_call: bool = True):
        """Export summary as Word document."""
        content = self.current_summary or self.view.get_response_content()
        if not content or not content.strip():
            if manual_call:
                self.view.show_error("No response content to export.")
            return
        
        export_prefs = self.view.get_export_preferences()
        
        # Determine filename
        if self.view.get_input_mode() == "file" and export_prefs["original_basename"]:
            filename = f"{export_prefs['original_basename']}_Summary.docx"
        elif self.current_youtube_title:
            filename = f"{self.current_youtube_title}_Summary.docx"
        else:
            filename = self.file_model.generate_timestamp_filename(format="docx")
        
        # Handle file location preferences
        file_path = None
        if export_prefs["use_original_location"] and export_prefs["original_directory"]:
            file_path = os.path.join(export_prefs["original_directory"], filename)
            try:
                self.file_model.export_to_docx(content, file_path)
            except Exception as e:
                logger.error(f"Failed to auto-export DOCX: {e}")
                file_path = None
        
        # If auto-export failed or not preferred, show save dialog
        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                initialfile=filename,
                filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            
            try:
                self.file_model.export_to_docx(content, file_path)
            except Exception as e:
                self.view.show_error(f"Failed to export DOCX: {e}")
                return
        
        if manual_call:
            self.view.show_success(f"Exported to {file_path}")
    
    def handle_copy_clicked(self):
        """Copy response content to clipboard."""
        content = self.view.get_response_content()
        if not content or not content.strip():
            self.view.show_error("Nothing to copy.")
            return
        
        try:
            if PYPERCLIP_AVAILABLE:
                pyperclip.copy(content)
            else:
                self.view.root.clipboard_clear()
                self.view.root.clipboard_append(content)
            self.view.show_success("Copied to clipboard.")
        except Exception as e:
            self.view.show_error(f"Failed to copy: {e}")
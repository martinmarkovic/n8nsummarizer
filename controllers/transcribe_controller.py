"""
Transcribe Controller - Coordinates Transcribe tab ↔ Models

Responsibilities:
    - Listen to Transcribe tab UI events
    - Call models to fetch transcripts and process them
    - Update view with results
    - Handle errors gracefully
    - Manage threading for blocking operations

Identical structure to FileController but for Transcribe tab.
Controller is THIN - just coordinates, doesn't contain business logic.
"""
import os
import threading
from tkinter import filedialog
from models.transcribe_model import TranscribeModel
from models.n8n_model import N8NModel
from models.file_model import FileModel
from utils.logger import logger
from config import EXPORT_DIR


class TranscribeController:
    """Coordinates Transcribe tab UI and models"""
    
    def __init__(self, view):
        """
        Initialize controller with view reference.
        
        Args:
            view: Transcribe tab view instance
        """
        self.view = view
        self.transcribe_model = TranscribeModel()
        self.n8n_model = N8NModel()
        self.file_model = FileModel()
        
        # Wire up view callbacks
        self.view.on_fetch_clicked = self.handle_fetch_clicked
        self.view.on_send_clicked = self.handle_send_clicked
        self.view.on_export_txt = self.handle_export_txt
        self.view.on_export_docx = self.handle_export_docx
        self.view.on_clear_clicked = self.handle_clear_clicked
        
        logger.info("TranscribeController initialized")
    
    def handle_fetch_clicked(self):
        """Handle Fetch Transcript button - starts background thread"""
        logger.info("Fetch transcript button clicked")
        
        url = self.view.get_youtube_url()
        
        if not url or not url.strip():
            self.view.show_error("Please enter a YouTube URL")
            return
        
        self.view.set_status("Fetching transcript...")
        self.view.show_loading(True)
        
        # Fetch in background thread
        thread = threading.Thread(
            target=self._fetch_transcript_thread,
            args=(url.strip(),),
            daemon=True
        )
        thread.start()
    
    def _fetch_transcript_thread(self, url: str):
        """Background thread function to fetch transcript"""
        try:
            # Use model to fetch transcript
            success, transcript, error = self.transcribe_model.get_transcript(url)
            
            if success:
                # Schedule UI update on main thread
                char_count = len(transcript)
                line_count = len(transcript.split('\n'))
                self.view.root.after(
                    0,
                    self._on_fetch_success,
                    transcript,
                    char_count,
                    line_count
                )
            else:
                self.view.root.after(0, self._on_fetch_error, error)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            self.view.root.after(0, self._on_fetch_error, error_msg)
    
    def _on_fetch_success(self, transcript: str, char_count: int, line_count: int):
        """Handle successful transcript fetch"""
        self.view.set_transcript(transcript)
        self.view.set_status(f"Transcript fetched ({char_count:,} characters, {line_count} lines)")
        self.view.show_loading(False)
    
    def _on_fetch_error(self, error_msg: str):
        """Handle transcript fetch error"""
        self.view.display_response(f"Error fetching transcript:\n\n{error_msg}")
        self.view.show_error(f"Failed to fetch transcript:\n{error_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def handle_send_clicked(self):
        """Handle Send to n8n button - starts background thread"""
        logger.info("Send button clicked")
        
        transcript = self.view.get_transcript()
        
        if not transcript or not transcript.strip():
            self.view.show_error("No transcript to send. Please fetch a transcript first.")
            return
        
        # Get webhook from GUI (with override support)
        webhook_override = self.view.get_webhook_override()
        gui_webhook_url = webhook_override['custom_url']
        
        if not gui_webhook_url or not gui_webhook_url.strip():
            self.view.show_error("Webhook URL in GUI is empty! Please enter a valid webhook URL.")
            return
        
        gui_webhook_url = gui_webhook_url.strip()
        
        # Save webhook if override is checked
        if webhook_override['override']:
            self.n8n_model.save_webhook_to_env(gui_webhook_url)
        
        # Prepare status message
        char_count = len(transcript)
        video_title = self.view.get_video_title() or "YouTube Video"
        status_msg = (
            f"Sending transcript to n8n...\n\n"
            f"Webhook: {gui_webhook_url}\n"
            f"Video: {video_title}\n"
            f"Transcript Size: {char_count:,} characters\n\n"
            f"Waiting for response..."
        )
        self.view.display_response(status_msg)
        self.view.set_status("Sending to n8n and waiting for response...")
        self.view.show_loading(True)
        
        # Send in background thread
        thread = threading.Thread(
            target=self._send_to_n8n_thread,
            args=(transcript, gui_webhook_url, webhook_override['override'], video_title),
            daemon=True
        )
        thread.start()
    
    def _send_to_n8n_thread(self, transcript: str, webhook_url: str, saved_to_env: bool, video_title: str):
        """Background thread function to send transcript to n8n"""
        try:
            # Override webhook in model
            self.n8n_model.webhook_url = webhook_url
            logger.info(f"Using webhook from GUI: {webhook_url}")
            
            # Send to n8n
            success, response_data, error = self.n8n_model.send_content(
                file_name=video_title or "transcript",
                content=transcript,
                metadata={
                    'type': 'youtube_transcript',
                    'characters': len(transcript),
                    'lines': len(transcript.split('\n'))
                }
            )
            
            if success:
                summary = self.n8n_model.extract_summary(response_data)
                saved_msg = " (saved to .env)" if saved_to_env else ""
                
                if summary:
                    self.view.root.after(
                        0,
                        self._on_send_success_with_summary,
                        summary,
                        video_title,
                        saved_msg
                    )
                else:
                    self.view.root.after(
                        0,
                        self._on_send_success_no_summary,
                        video_title,
                        saved_msg
                    )
            else:
                self.view.root.after(0, self._on_send_error, error)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            self.view.root.after(0, self._on_send_error, error_msg)
    
    def _on_send_success_with_summary(self, summary: str, video_title: str, saved_msg: str):
        """Handle successful summarization response"""
        self.view.display_response(summary)
        
        success_msg = f"Summarization received for '{video_title}'!{saved_msg}"
        self.view.show_success(success_msg)
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_send_success_no_summary(self, video_title: str, saved_msg: str):
        """Handle successful send with no summary in response"""
        self.view.display_response("Request sent successfully.\n\nNo summary returned from n8n workflow.")
        self.view.show_success(f"Successfully sent '{video_title}' to n8n!{saved_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_send_error(self, error_msg: str):
        """Handle error response"""
        self.view.display_response(f"Error occurred:\n\n{error_msg}")
        self.view.show_error(f"Failed to send to n8n:\n{error_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def handle_export_txt(self):
        """Export transcript or response as .txt file"""
        # Try response first, fall back to transcript
        content = self.view.get_response_content()
        if not content or not content.strip():
            content = self.view.get_transcript()
        
        if not content or not content.strip():
            self.view.show_error("No content to export!")
            return
        
        # Determine filename
        video_title = self.view.get_video_title() or "transcript"
        default_filename = f"{video_title}_Summary.txt"
        
        # Show file dialog
        file_path = filedialog.asksaveasfilename(
            title="Export Transcript/Response as .txt",
            defaultextension=".txt",
            initialdir=EXPORT_DIR,
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_path:
            self._save_txt_file(file_path, content)
    
    def _save_txt_file(self, file_path: str, content: str):
        """Save content to .txt file using FileModel"""
        success, message = self.file_model.export_txt(content, file_path)
        
        if success:
            self.view.show_success(f"Exported successfully to:\n{file_path}")
            self.view.set_status(f"Exported to {os.path.basename(file_path)}")
        else:
            self.view.show_error(message)
    
    def handle_export_docx(self):
        """Export transcript or response as .docx file"""
        # Try response first, fall back to transcript
        content = self.view.get_response_content()
        if not content or not content.strip():
            content = self.view.get_transcript()
        
        if not content or not content.strip():
            self.view.show_error("No content to export!")
            return
        
        # Check if docx library is available
        try:
            import docx
        except ImportError:
            self.view.show_error(
                "python-docx library not installed!\n\n"
                "Install it with: pip install python-docx"
            )
            return
        
        # Determine filename
        video_title = self.view.get_video_title() or "transcript"
        default_filename = f"{video_title}_Summary.docx"
        
        # Show file dialog
        file_path = filedialog.asksaveasfilename(
            title="Export Transcript/Response as .docx",
            defaultextension=".docx",
            initialdir=EXPORT_DIR,
            initialfile=default_filename,
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        
        if file_path:
            self._save_docx_file(file_path, content)
    
    def _save_docx_file(self, file_path: str, content: str):
        """Save content to .docx file using FileModel"""
        success, message = self.file_model.export_docx(content, file_path)
        
        if success:
            self.view.show_success(f"Exported successfully to:\n{file_path}")
            self.view.set_status(f"Exported to {os.path.basename(file_path)}")
        else:
            self.view.show_error(message)
    
    def handle_clear_clicked(self):
        """Handle Clear button"""
        logger.info("Clear button clicked")
        self.view.clear_all()
        self.view.set_status("Ready")
    
    def test_n8n_connection(self) -> bool:
        """Test n8n webhook connectivity"""
        logger.info("Testing n8n connection...")
        is_connected = self.n8n_model.test_connection()
        
        if is_connected:
            self.view.set_status("n8n server is reachable")
            logger.info("n8n connection test passed")
        else:
            self.view.show_error("Cannot reach n8n server. Check if it's running at the configured URL.")
            logger.warning("n8n connection test failed")
        
        return is_connected

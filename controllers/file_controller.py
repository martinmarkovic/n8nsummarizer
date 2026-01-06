"""
File Controller - Coordinates File tab ↔ Models

Responsibilities:
    - Listen to File tab UI events
    - Call models to process data
    - Update view with results
    - Handle errors gracefully
    - Manage threading for blocking operations

Controller is THIN - just coordinates, doesn't contain business logic.
"""
import os
import threading
from datetime import datetime
from tkinter import filedialog
from models.file_model import FileModel
from models.n8n_model import N8NModel
from utils.logger import logger
from config import EXPORT_DIR


class FileController:
    """Coordinates File tab UI and models"""
    
    def __init__(self, view):
        """
        Initialize controller with view reference.
        
        Args:
            view: File tab view instance
        """
        self.view = view
        self.file_model = FileModel()
        self.n8n_model = N8NModel()
        
        # Wire up view callbacks
        self.view.on_file_selected = self.handle_file_selected
        self.view.on_send_clicked = self.handle_send_clicked
        self.view.on_clear_clicked = self.handle_clear_clicked
        self.view.on_export_txt = self.handle_export_txt
        self.view.on_export_docx = self.handle_export_docx
        
        logger.info("FileController initialized")
    
    def handle_file_selected(self, file_path: str):
        """Handle file selection from view"""
        logger.info(f"File selected: {file_path}")
        
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
        """Handle Send to n8n button - starts background thread"""
        logger.info("Send button clicked")
        
        # Validate file is loaded
        file_path = self.view.get_file_path()
        if not file_path:
            self.view.show_error("No file loaded. Please select a file first.")
            return
        
        content = self.view.get_content()
        if not content or not content.strip():
            self.view.show_error("File content is empty. Cannot send empty content.")
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
        
        # Save export preferences to .env
        try:
            export_prefs = self.view.get_export_preferences()
            self._save_export_preferences_to_env(export_prefs)
        except Exception as e:
            logger.error(f"Failed to save export preferences: {e}")
        
        # Get file info for display
        file_info = self.file_model.get_file_info(file_path)
        status_msg = (
            f"Sending request to n8n...\n\n"
            f"Webhook: {gui_webhook_url}\n"
            f"File: {file_info['name']}\n"
            f"Size: {file_info['size_kb']:.2f} KB\n\n"
            f"Waiting for response..."
        )
        self.view.display_response(status_msg)
        self.view.set_status("Sending to n8n and waiting for response...")
        self.view.show_loading(True)
        
        # Send in background thread
        thread = threading.Thread(
            target=self._send_to_n8n_thread,
            args=(file_path, file_info, content, gui_webhook_url, webhook_override['override']),
            daemon=True
        )
        thread.start()
    
    def _send_to_n8n_thread(self, file_path: str, file_info: dict, content: str, webhook_url: str, saved_to_env: bool):
        """Background thread function to send request to n8n"""
        try:
            # Override webhook in model
            self.n8n_model.webhook_url = webhook_url
            logger.info(f"Using webhook from GUI: {webhook_url}")
            
            # Get actual file size in bytes
            file_size_bytes = os.path.getsize(file_path)
            logger.debug(f"File size: {file_size_bytes} bytes ({file_size_bytes/1024:.1f} KB)")
            
            # Send to n8n with FILE SIZE IN BYTES (v4.4.4 CRITICAL FIX!)
            success, response_data, error = self.n8n_model.send_content(
                file_name=file_info['name'],
                content=content,
                file_size_bytes=file_size_bytes,  # v4.4.4: PASS FILE SIZE IN BYTES!
                metadata={
                    'size_bytes': file_info['size'],
                    'lines': file_info['lines']
                }
            )
            
            if success:
                summary = self.n8n_model.extract_summary(response_data)
                saved_msg = " (saved to .env)" if saved_to_env else ""
                
                if summary:
                    # Schedule UI update on main thread
                    self.view.root.after(
                        0,
                        self._on_success_with_summary,
                        summary,
                        file_info['name'],
                        saved_msg
                    )
                else:
                    self.view.root.after(
                        0,
                        self._on_success_no_summary,
                        file_info['name'],
                        saved_msg
                    )
            else:
                self.view.root.after(0, self._on_error, error)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            self.view.root.after(0, self._on_error, error_msg)
    
    def _on_success_with_summary(self, summary: str, file_name: str, saved_msg: str):
        """Handle successful summarization response"""
        self.view.display_response(summary)
        
        # Check if auto-export is enabled
        export_prefs = self.view.get_export_preferences()
        auto_txt = export_prefs['auto_export_txt']
        auto_docx = export_prefs['auto_export_docx']
        
        if auto_txt or auto_docx:
            logger.info(f"Auto-export enabled - .txt: {auto_txt}, .docx: {auto_docx}")
            self._auto_export_response(summary, auto_txt, auto_docx)
            
            exported_formats = []
            if auto_txt:
                exported_formats.append('.txt')
            if auto_docx:
                exported_formats.append('.docx')
            
            formats_str = ' and '.join(exported_formats)
            success_msg = f"Summarization received and auto-exported as {formats_str} for '{file_name}'!{saved_msg}"
        else:
            success_msg = f"Summarization received for '{file_name}'!{saved_msg}"
        
        self.view.show_success(success_msg)
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_success_no_summary(self, file_name: str, saved_msg: str):
        """Handle successful send with no summary in response"""
        self.view.display_response("Request sent successfully.\n\nNo summary returned from n8n workflow.")
        self.view.show_success(f"Successfully sent '{file_name}' to n8n!{saved_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_error(self, error_msg: str):
        """Handle error response"""
        self.view.display_response(f"Error occurred:\n\n{error_msg}")
        self.view.show_error(f"Failed to send to n8n:\n{error_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def handle_export_txt(self, manual_call: bool = True):
        """Export response content as .txt file"""
        response_content = self.view.get_response_content()
        
        if not response_content or not response_content.strip():
            self.view.show_error("No response content to export!")
            return
        
        # Get export preferences
        export_prefs = self.view.get_export_preferences()
        file_path = self.view.get_file_path()
        
        # Determine filename
        if export_prefs['original_basename']:
            default_filename = f"{export_prefs['original_basename']}_Summary.txt"
        else:
            default_filename = self.file_model.generate_timestamp_filename(format="txt")
        
        # Determine directory
        if export_prefs['use_original_location'] and export_prefs['original_directory']:
            # Auto-save without dialog
            file_path = os.path.join(export_prefs['original_directory'], default_filename)
            self._save_txt_file(file_path, response_content)
        else:
            # Show file dialog
            file_path = filedialog.asksaveasfilename(
                title="Export Response as .txt",
                defaultextension=".txt",
                initialdir=EXPORT_DIR,
                initialfile=default_filename,
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            
            if file_path:
                self._save_txt_file(file_path, response_content)
    
    def _save_txt_file(self, file_path: str, content: str, silent: bool = False):
        """Save content to .txt file using FileModel"""
        success, message = self.file_model.export_txt(content, file_path)
        
        if success:
            if not silent:
                self.view.show_success(f"Response exported successfully to:\n{file_path}")
                self.view.set_status(f"Exported to {os.path.basename(file_path)}")
        else:
            if not silent:
                self.view.show_error(message)
    
    def handle_export_docx(self):
        """Export response content as .docx file"""
        response_content = self.view.get_response_content()
        
        if not response_content or not response_content.strip():
            self.view.show_error("No response content to export!")
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
        
        # Get export preferences
        export_prefs = self.view.get_export_preferences()
        
        # Determine filename
        if export_prefs['original_basename']:
            default_filename = f"{export_prefs['original_basename']}_Summary.docx"
        else:
            default_filename = self.file_model.generate_timestamp_filename(format="docx")
        
        # Determine directory
        if export_prefs['use_original_location'] and export_prefs['original_directory']:
            # Auto-save without dialog
            file_path = os.path.join(export_prefs['original_directory'], default_filename)
            self._save_docx_file(file_path, response_content)
        else:
            # Show file dialog
            file_path = filedialog.asksaveasfilename(
                title="Export Response as .docx",
                defaultextension=".docx",
                initialdir=EXPORT_DIR,
                initialfile=default_filename,
                filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
            )
            
            if file_path:
                self._save_docx_file(file_path, response_content)
    
    def _save_docx_file(self, file_path: str, content: str, silent: bool = False):
        """Save content to .docx file using FileModel"""
        success, message = self.file_model.export_docx(content, file_path)
        
        if success:
            if not silent:
                self.view.show_success(f"Response exported successfully to:\n{file_path}")
                self.view.set_status(f"Exported to {os.path.basename(file_path)}")
        else:
            if not silent:
                self.view.show_error(message)
    
    def _auto_export_response(self, response_content: str, export_txt: bool = True, export_docx: bool = True):
        """Auto-export response as .txt and/or .docx"""
        export_prefs = self.view.get_export_preferences()
        
        # Determine base filename
        if export_prefs['original_basename']:
            base_filename = f"{export_prefs['original_basename']}_Summary"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"n8n_response_{timestamp}"
        
        # Determine save directory
        if export_prefs['use_original_location'] and export_prefs['original_directory']:
            save_dir = export_prefs['original_directory']
        else:
            save_dir = EXPORT_DIR
        
        # Export .txt if enabled
        if export_txt:
            txt_path = os.path.join(save_dir, f"{base_filename}.txt")
            self._save_txt_file(txt_path, response_content, silent=True)
        
        # Export .docx if enabled
        if export_docx:
            docx_path = os.path.join(save_dir, f"{base_filename}.docx")
            self._save_docx_file(docx_path, response_content, silent=True)
    
    def _save_export_preferences_to_env(self, export_prefs: dict):
        """Save export preferences to .env file"""
        env_file = '.env'
        env_lines = []
        
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Track which preferences were found
        found = {
            'use_original_location': False,
            'auto_txt': False,
            'auto_docx': False
        }
        
        new_lines = []
        for line in env_lines:
            if line.strip().startswith('EXPORT_USE_ORIGINAL_LOCATION='):
                new_lines.append(f"EXPORT_USE_ORIGINAL_LOCATION={'true' if export_prefs['use_original_location'] else 'false'}\n")
                found['use_original_location'] = True
            elif line.strip().startswith('EXPORT_AUTO_TXT='):
                new_lines.append(f"EXPORT_AUTO_TXT={'true' if export_prefs['auto_export_txt'] else 'false'}\n")
                found['auto_txt'] = True
            elif line.strip().startswith('EXPORT_AUTO_DOCX='):
                new_lines.append(f"EXPORT_AUTO_DOCX={'true' if export_prefs['auto_export_docx'] else 'false'}\n")
                found['auto_docx'] = True
            else:
                new_lines.append(line)
        
        # Add missing preferences
        if not found['use_original_location']:
            new_lines.append(f"EXPORT_USE_ORIGINAL_LOCATION={'true' if export_prefs['use_original_location'] else 'false'}\n")
        if not found['auto_txt']:
            new_lines.append(f"EXPORT_AUTO_TXT={'true' if export_prefs['auto_export_txt'] else 'false'}\n")
        if not found['auto_docx']:
            new_lines.append(f"EXPORT_AUTO_DOCX={'true' if export_prefs['auto_export_docx'] else 'false'}\n")
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        logger.info(f"Export preferences saved to .env")
    
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

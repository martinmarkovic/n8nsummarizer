"""
Scanner Controller - Coordinates between View and Models with webhook override + threading
"""
import os
import threading
from models.file_scanner import FileScanner
from models.http_client import HTTPClient
from utils.logger import logger


class ScannerController:
    """Controller for coordinating file scanning and HTTP transmission with webhook override"""
    
    def __init__(self, view):
        self.view = view
        self.file_scanner = FileScanner()
        self.http_client = HTTPClient()
        
        # Setup view callbacks
        self.view.on_file_selected = self.handle_file_selected
        self.view.on_send_clicked = self.handle_send_clicked
        self.view.on_clear_clicked = self.handle_clear_clicked
        
        logger.info("ScannerController initialized")
    
    def handle_file_selected(self, file_path):
        """Handle file selection from view"""
        logger.info(f"File selected: {file_path}")
        
        # Read file using model
        success, content, error = self.file_scanner.read_file(file_path)
        
        if success:
            # Update view with file content and info
            self.view.set_file_path(file_path)
            self.view.set_content(content)
            
            file_info = self.file_scanner.get_file_info()
            self.view.set_file_info(file_info)
            
            self.view.set_status(f"File loaded: {file_info['name']}")
        else:
            # Show error
            self.view.show_error(f"Failed to load file: {error}")
            self.view.set_file_path(None)
            self.view.set_content("")
            self.view.set_file_info(None)
    
    def handle_send_clicked(self):
        """Handle send button click - starts background thread for n8n request"""
        logger.info("Send button clicked")
        
        # Validate file is loaded
        if not self.file_scanner.current_file:
            self.view.show_error("No file loaded. Please select a file first.")
            return
        
        # Get content from view (user might have edited it)
        content = self.view.get_content()
        
        if not content or not content.strip():
            self.view.show_error("File content is empty. Cannot send empty content.")
            return
        
        # Get webhook from GUI
        webhook_override = self.view.get_webhook_override()
        gui_webhook_url = webhook_override['custom_url']
        
        if not gui_webhook_url or not gui_webhook_url.strip():
            self.view.show_error("Webhook URL in GUI is empty! Please enter a valid webhook URL.")
            return
        
        gui_webhook_url = gui_webhook_url.strip()
        
        # If checkbox is checked, save to .env
        if webhook_override['override']:
            try:
                self._save_webhook_to_env(gui_webhook_url)
                logger.info(f"Saved webhook to .env: {gui_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to save webhook to .env: {e}")
                self.view.show_error(f"Warning: Could not save to .env file: {e}")
                # Continue anyway - still send the request
        
        # Show initial status in response box
        file_info = self.file_scanner.get_file_info()
        status_msg = f"⏳ Sending request to n8n...\n\nWebhook: {gui_webhook_url}\nFile: {file_info['name']}\nSize: {file_info['size_kb']:.2f} KB\n\nWaiting for response..."
        self.view.display_response(status_msg)
        
        # Show loading state
        self.view.set_status("Sending to n8n and waiting for response...")
        self.view.show_loading(True)
        
        # Run request in background thread to prevent GUI freeze
        thread = threading.Thread(
            target=self._send_to_n8n_thread,
            args=(file_info, content, gui_webhook_url, webhook_override['override']),
            daemon=True
        )
        thread.start()
    
    def _send_to_n8n_thread(self, file_info, content, webhook_url, saved_to_env):
        """Background thread function to send request to n8n"""
        try:
            # ALWAYS use GUI webhook
            self.http_client.webhook_url = webhook_url
            logger.info(f"Using webhook from GUI: {webhook_url}")
            
            # Send via HTTP using model - this blocks until response is received
            success, response_data, error = self.http_client.send_to_n8n(
                file_name=file_info['name'],
                content=content,
                metadata={
                    'size_bytes': file_info['size'],
                    'lines': file_info['lines']
                }
            )
            
            # Update UI from main thread using after()
            if success:
                # Extract summarization from response
                summary = self._extract_summary(response_data)
                
                saved_msg = " (saved to .env)" if saved_to_env else ""
                
                if summary:
                    # Clear previous status and display summary
                    self.view.root.after(0, self._on_success_with_summary, summary, file_info['name'], saved_msg)
                else:
                    self.view.root.after(0, self._on_success_no_summary, file_info['name'], saved_msg)
            else:
                self.view.root.after(0, self._on_error, error)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            self.view.root.after(0, self._on_error, error_msg)
    
    def _on_success_with_summary(self, summary, file_name, saved_msg):
        """Called from main thread when summary is received"""
        self.view.display_response(summary)
        self.view.show_success(f"Summarization received for '{file_name}'!{saved_msg}")
        logger.info("Summarization successfully received")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_success_no_summary(self, file_name, saved_msg):
        """Called from main thread when request succeeds but no summary"""
        self.view.display_response("✓ Request sent successfully\n\nNo summary returned from n8n workflow.")
        self.view.show_success(f"Successfully sent '{file_name}' to n8n!{saved_msg}")
        logger.info("File successfully sent to n8n (no summary in response)")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _on_error(self, error_msg):
        """Called from main thread when error occurs"""
        self.view.display_response(f"❌ Error\n\n{error_msg}")
        self.view.show_error(f"Failed to send to n8n:\n{error_msg}")
        logger.error(f"Send failed: {error_msg}")
        self.view.set_status("Ready")
        self.view.show_loading(False)
    
    def _save_webhook_to_env(self, webhook_url):
        """Save webhook URL to .env file"""
        env_file = '.env'
        env_lines = []
        webhook_found = False
        
        # Read existing .env if it exists
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Update or add N8N_WEBHOOK_URL
        new_lines = []
        for line in env_lines:
            if line.strip().startswith('N8N_WEBHOOK_URL='):
                new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
                webhook_found = True
            else:
                new_lines.append(line)
        
        # If not found, add it
        if not webhook_found:
            new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
        
        # Write back to .env
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        logger.info(f"Updated .env file with webhook: {webhook_url}")
    
    def _extract_summary(self, response_data):
        """
        Extract summary from n8n response
        
        Args:
            response_data: Response from n8n (dict or str)
            
        Returns:
            str: Extracted summary or None
        """
        if response_data is None:
            return None
        
        # If it's a string, return it
        if isinstance(response_data, str):
            return response_data
        
        # If it's a dict, try common keys
        if isinstance(response_data, dict):
            # Try common response keys
            for key in ['summary', 'summarization', 'result', 'output', 'text', 'content']:
                if key in response_data:
                    return response_data[key]
            
            # If no common key found, return formatted JSON
            import json
            return json.dumps(response_data, indent=2)
        
        return str(response_data)
    
    def handle_clear_clicked(self):
        """Handle clear button click from view"""
        logger.info("Clear button clicked")
        
        self.file_scanner.clear()
        self.view.clear_all()
        self.view.set_status("Ready")
    
    def test_n8n_connection(self):
        """Test connectivity to n8n server"""
        logger.info("Testing n8n connection...")
        is_connected = self.http_client.test_connection()
        
        if is_connected:
            self.view.set_status("✓ n8n server is reachable")
            logger.info("n8n connection test passed")
        else:
            self.view.show_error("Cannot reach n8n server. Check if it's running at the configured URL.")
            logger.warning("n8n connection test failed")
        
        return is_connected

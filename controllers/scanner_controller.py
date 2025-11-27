"""
Scanner Controller - Coordinates between View and Models
"""
from models.file_scanner import FileScanner
from models.http_client import HTTPClient
from utils.logger import logger


class ScannerController:
    """Controller for coordinating file scanning and HTTP transmission"""
    
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
        """Handle send button click from view"""
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
        
        # Show loading state
        self.view.set_status("Sending to n8n and waiting for response...")
        self.view.show_loading(True)
        
        try:
            # Get file info
            file_info = self.file_scanner.get_file_info()
            
            # Send via HTTP using model - this waits for response
            success, response_data, error = self.http_client.send_to_n8n(
                file_name=file_info['name'],
                content=content,
                metadata={
                    'size_bytes': file_info['size'],
                    'lines': file_info['lines']
                }
            )
            
            if success:
                # Extract summarization from response
                summary = self._extract_summary(response_data)
                
                if summary:
                    # Display the summary in the view
                    self.view.display_response(summary)
                    self.view.show_success(f"Summarization received for '{file_info['name']}'!")
                    logger.info("Summarization successfully received")
                else:
                    self.view.show_success(f"Successfully sent '{file_info['name']}' to n8n!")
                    logger.info("File successfully sent to n8n (no summary in response)")
                
                self.view.set_status("Ready")
            else:
                self.view.show_error(f"Failed to send to n8n:\n{error}")
                logger.error(f"Send failed: {error}")
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.view.show_error(error_msg)
            logger.error(error_msg)
        
        finally:
            self.view.show_loading(False)
    
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

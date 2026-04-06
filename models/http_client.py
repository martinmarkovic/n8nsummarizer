"""
HTTP Client Model - Handles communication with n8n server
"""
import requests
import json
from config import N8N_WEBHOOK_URL, N8N_TIMEOUT
from utils.logger import logger


class HTTPClient:
    """Model for HTTP communication with n8n webhook"""
    
    def __init__(self, webhook_url=N8N_WEBHOOK_URL, timeout=N8N_TIMEOUT):
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.last_response = None
    
    def send_to_n8n(self, file_name, content, metadata=None):
        """
        Send file content to n8n webhook and wait for response
        
        Args:
            file_name (str): Name of the file
            content (str): File content
            metadata (dict): Optional metadata to send
            
        Returns:
            tuple: (success: bool, response_data: dict or str, error_msg: str or None)
        """
        if not self.webhook_url:
            error_msg = "N8N webhook URL not configured"
            logger.error(error_msg)
            return False, None, error_msg
        
        try:
            payload = {
                'file_name': file_name,
                'content': content,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }
            
            if metadata:
                payload['metadata'] = metadata
            
            logger.info(f"Sending to n8n: {self.webhook_url}")
            logger.debug(f"Payload size: {len(json.dumps(payload))} bytes")
            
            # Make POST request - this blocks until response is received
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            self.last_response = response
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully received response from n8n (Status: {response.status_code})")
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                    logger.debug(f"Parsed JSON response: {response_data}")
                    return True, response_data, None
                except json.JSONDecodeError:
                    # If not JSON, return text
                    logger.debug(f"Response is not JSON, returning text")
                    return True, response.text, None
            else:
                error_msg = f"n8n server returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout (>{self.timeout}s) - n8n processing may be taking too long"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error - cannot reach n8n at {self.webhook_url}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error sending to n8n: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def test_connection(self):
        """Test n8n webhook connectivity"""
        try:
            logger.info(f"Testing connection to {self.webhook_url}")
            response = requests.post(
                self.webhook_url,
                json={'test': True},
                timeout=5
            )
            return response.status_code in [200, 201, 202, 400, 404]
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_last_response(self):
        """Get last HTTP response object"""
        return self.last_response

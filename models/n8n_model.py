"""
N8N Model - Business logic for n8n webhook communication

Responsibilities:
    - Send requests to n8n webhook
    - Handle responses and response extraction
    - Manage timeouts and retries
    - Process webhook overrides
    - Save webhook configuration to .env

This is PURE business logic - NO UI dependencies.
Reusable by any controller (File tab, Transcribe tab, etc.)
"""
import os
import json
import requests
from datetime import datetime
from config import N8N_WEBHOOK_URL, N8N_TIMEOUT
from utils.logger import logger


class N8NModel:
    """Handles n8n webhook communication and webhook management"""
    
    def __init__(self, webhook_url: str = None, timeout: int = None):
        """
        Initialize n8n client.
        
        Args:
            webhook_url (str): Override default webhook URL from config
            timeout (int): Request timeout in seconds
        """
        self.webhook_url = webhook_url or N8N_WEBHOOK_URL
        self.timeout = timeout or N8N_TIMEOUT
        self.last_response = None
    
    def send_content(self, file_name: str, content: str, 
                    metadata: dict = None) -> tuple[bool, dict, str]:
        """
        Send content to n8n for processing.
        
        Args:
            file_name (str): Name of file
            content (str): Content to send
            metadata (dict): Optional metadata
            
        Returns:
            tuple: (success: bool, response_data: dict or str, error_msg: str or None)
            
        Example:
            >>> model = N8NModel()
            >>> success, response, error = model.send_content(
            ...     'document.txt',
            ...     'Content here',
            ...     {'size_bytes': 1024}
            ... )
            >>> if success:
            ...     print(response['summary'])
        """
        if not self.webhook_url:
            error = "n8n webhook URL not configured"
            logger.error(error)
            return False, None, error
        
        try:
            payload = {
                'file_name': file_name,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            
            if metadata:
                payload['metadata'] = metadata
            
            logger.info(f"Sending to n8n: {self.webhook_url}")
            logger.debug(f"Payload size: {len(json.dumps(payload))} bytes")
            
            # Send request - blocks until response received
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            self.last_response = response
            
            # Check status
            if response.status_code not in [200, 201, 202]:
                error = f"n8n returned {response.status_code}: {response.text}"
                logger.error(error)
                return False, None, error
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.info(f"Successfully received JSON response from n8n (Status: {response.status_code})")
                logger.debug(f"Response: {response_data}")
            except json.JSONDecodeError:
                response_data = response.text
                logger.info(f"Successfully received text response from n8n (Status: {response.status_code})")
            
            return True, response_data, None
        
        except requests.exceptions.Timeout:
            error = f"Request timeout (>{self.timeout}s) - n8n processing may be taking too long"
            logger.error(error)
            return False, None, error
        except requests.exceptions.ConnectionError as e:
            error = f"Cannot reach n8n at {self.webhook_url}: {str(e)}"
            logger.error(error)
            return False, None, error
        except requests.exceptions.RequestException as e:
            error = f"HTTP request failed: {str(e)}"
            logger.error(error)
            return False, None, error
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(error)
            return False, None, error
    
    def test_connection(self) -> bool:
        """
        Test webhook connectivity.
        
        Returns:
            bool: True if webhook is reachable, False otherwise
        """
        try:
            logger.info(f"Testing connection to {self.webhook_url}")
            response = requests.post(
                self.webhook_url,
                json={'test': True},
                timeout=5
            )
            is_reachable = response.status_code in [200, 201, 202, 400, 404]
            if is_reachable:
                logger.info("n8n connection test passed")
            else:
                logger.warning(f"n8n returned unexpected status: {response.status_code}")
            return is_reachable
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def extract_summary(self, response_data) -> str:
        """
        Extract summary from n8n response.
        Tries multiple common keys: summary, summarization, result, output, text, content
        
        Args:
            response_data: Response from n8n (dict, str, etc.)
            
        Returns:
            str: Extracted summary or stringified response
        """
        if response_data is None:
            return None
        
        if isinstance(response_data, str):
            return response_data
        
        if isinstance(response_data, dict):
            # Try common keys
            for key in ['summary', 'summarization', 'result', 'output', 'text', 'content']:
                if key in response_data:
                    value = response_data[key]
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, dict):
                        return json.dumps(value, indent=2)
                    else:
                        return str(value)
            
            # If no common keys, return pretty-printed JSON
            return json.dumps(response_data, indent=2)
        
        return str(response_data)
    
    def save_webhook_to_env(self, webhook_url: str) -> bool:
        """
        Save webhook URL to .env file.
        
        Args:
            webhook_url (str): Webhook URL to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            env_file = '.env'
            env_lines = []
            webhook_found = False
            
            if os.path.exists(env_file):
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()
            
            new_lines = []
            for line in env_lines:
                if line.strip().startswith('N8N_WEBHOOK_URL='):
                    new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
                    webhook_found = True
                else:
                    new_lines.append(line)
            
            if not webhook_found:
                new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
            
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info(f"Saved webhook to .env: {webhook_url}")
            self.webhook_url = webhook_url
            return True
        except Exception as e:
            logger.error(f"Failed to save webhook to .env: {e}")
            return False
    
    def get_last_response(self):
        """Get last HTTP response object (for debugging)"""
        return self.last_response

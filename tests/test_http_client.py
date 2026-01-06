"""
Unit tests for HTTPClient model
"""
import unittest
from unittest.mock import patch, MagicMock
from models.http_client import HTTPClient


class TestHTTPClient(unittest.TestCase):
    """Test cases for HTTPClient model"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.client = HTTPClient(webhook_url='http://localhost:5678/webhook/test')
    
    @patch('requests.post')
    def test_send_successful(self, mock_post):
        """Test successful send to n8n"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response
        
        success, response, error = self.client.send_to_n8n('test.txt', 'Test content')
        
        self.assertTrue(success)
        self.assertIsNotNone(response)
        self.assertIsNone(error)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_server_error(self, mock_post):
        """Test send with server error"""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        success, response, error = self.client.send_to_n8n('test.txt', 'Test content')
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    @patch('requests.post')
    def test_send_timeout(self, mock_post):
        """Test send with timeout"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        success, response, error = self.client.send_to_n8n('test.txt', 'Test content')
        
        self.assertFalse(success)
        self.assertIn('timeout', error.lower())
    
    @patch('requests.post')
    def test_send_connection_error(self, mock_post):
        """Test send with connection error"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        success, response, error = self.client.send_to_n8n('test.txt', 'Test content')
        
        self.assertFalse(success)
        self.assertIn('connection', error.lower())
    
    def test_no_webhook_url(self):
        """Test send with no webhook URL configured"""
        client = HTTPClient(webhook_url='')
        success, response, error = client.send_to_n8n('test.txt', 'Test content')
        
        self.assertFalse(success)
        self.assertIn('not configured', error.lower())
    
    @patch('requests.post')
    def test_test_connection_success(self, mock_post):
        """Test successful connection test"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        is_connected = self.client.test_connection()
        self.assertTrue(is_connected)
    
    @patch('requests.post')
    def test_test_connection_failure(self, mock_post):
        """Test failed connection test"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        is_connected = self.client.test_connection()
        self.assertFalse(is_connected)


if __name__ == '__main__':
    unittest.main()
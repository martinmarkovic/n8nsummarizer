"""
Unit tests for FileScanner model
"""
import unittest
import tempfile
import os
from models.file_scanner import FileScanner


class TestFileScanner(unittest.TestCase):
    """Test cases for FileScanner model"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.scanner = FileScanner()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup after tests"""
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_read_valid_file(self):
        """Test reading a valid text file"""
        # Create temp file
        test_file = os.path.join(self.temp_dir, "test.txt")
        test_content = "Hello, World!\nThis is a test."
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Read file
        success, content, error = self.scanner.read_file(test_file)
        
        self.assertTrue(success)
        self.assertEqual(content, test_content)
        self.assertIsNone(error)
    
    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file"""
        success, content, error = self.scanner.read_file("/nonexistent/file.txt")
        
        self.assertFalse(success)
        self.assertIsNone(content)
        self.assertIsNotNone(error)
    
    def test_read_empty_file(self):
        """Test reading an empty file"""
        test_file = os.path.join(self.temp_dir, "empty.txt")
        with open(test_file, 'w') as f:
            pass
        
        success, content, error = self.scanner.read_file(test_file)
        
        self.assertFalse(success)
        self.assertIsNone(content)
        self.assertIn("empty", error.lower())
    
    def test_get_file_info(self):
        """Test getting file information"""
        test_file = os.path.join(self.temp_dir, "info.txt")
        test_content = "Line 1\nLine 2\nLine 3"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        self.scanner.read_file(test_file)
        info = self.scanner.get_file_info()
        
        self.assertIsNotNone(info)
        self.assertEqual(info['name'], 'info.txt')
        self.assertEqual(info['lines'], 3)
        self.assertGreater(info['size'], 0)
    
    def test_clear(self):
        """Test clearing current file"""
        test_file = os.path.join(self.temp_dir, "clear.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        self.scanner.read_file(test_file)
        self.assertIsNotNone(self.scanner.current_file)
        
        self.scanner.clear()
        self.assertIsNone(self.scanner.current_file)
        self.assertIsNone(self.scanner.current_content)


if __name__ == '__main__':
    unittest.main()
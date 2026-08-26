#!/usr/bin/env python3
"""
Test suite for SummarizerController (v9.3)

Comprehensive tests for the unified summarization controller.
"""

import sys
import os
import tkinter as tk
from unittest.mock import Mock, MagicMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that SummarizerController can be imported correctly."""
    print("Testing SummarizerController import...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        print("[OK] SummarizerController imported successfully")
        return True
        
    except Exception as e:
        print(f"[FAILED] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_initialization():
    """Test SummarizerController initialization."""
    print("\nTesting SummarizerController initialization...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        # Create mock view
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        # Create controller
        controller = SummarizerController(mock_view)
        
        # Verify initialization
        assert controller.view == mock_view
        assert hasattr(controller, 'file_model')
        assert hasattr(controller, 'llm_client')
        assert hasattr(controller, 'transcribe_model')
        assert hasattr(controller, 'current_summary')
        assert hasattr(controller, 'current_transcript')
        
        print("[OK] Controller initialized successfully")
        print("[OK] All required attributes present")
        
        # Clean up
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_callback_wiring():
    """Test that view callbacks are properly wired."""
    print("\nTesting callback wiring...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        controller = SummarizerController(mock_view)
        
        # Verify callbacks are set
        assert mock_view.on_file_selected is not None
        assert mock_view.on_send_clicked is not None
        assert mock_view.on_export_txt is not None
        assert mock_view.on_export_docx is not None
        assert mock_view.on_copy_clicked is not None
        
        print("[OK] File selected callback wired")
        print("[OK] Send clicked callback wired")
        print("[OK] Export callbacks wired")
        print("[OK] Copy callback wired")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Callback wiring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_handling():
    """Test file handling workflow."""
    print("\nTesting file handling workflow...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        # Mock file model methods
        with patch.object(mock_view, 'set_file_path'), \
             patch.object(mock_view, 'set_content'), \
             patch.object(mock_view, 'set_file_info'), \
             patch.object(mock_view, 'set_status') as mock_status:
            
            controller = SummarizerController(mock_view)
            
            # Mock file model read_file to return success
            with patch.object(controller.file_model, 'read_file', return_value=(True, "test content", None)), \
                 patch.object(controller.file_model, 'get_file_info', return_value({'name': 'test.txt', 'size_kb': 1.0, 'lines': 10, 'type': 'Text File'})):
                
                # Call handle_file_selected
                controller.handle_file_selected("/test/file.txt")
                
                # Verify view methods were called
                assert mock_view.set_file_path.called
                assert mock_view.set_content.called
                assert mock_view.set_file_info.called
                assert mock_status.called
                
        print("[OK] File handling workflow works")
        print("[OK] View methods called correctly")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] File handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_configuration():
    """Test LLM client configuration."""
    print("\nTesting LLM configuration...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        controller = SummarizerController(mock_view)
        
        # Test with valid configuration
        with patch.object(mock_view, 'get_webhook_url', return_value="http://test.example.com"), \
             patch.object(mock_view, 'get_model_name', return_value="test-model"), \
             patch.object(mock_view, 'get_save_settings', return_value=False):
            
            result = controller._update_llm_client()
            assert result == True
            assert controller.llm_client.config.webhook_url == "http://test.example.com"
            assert controller.llm_client.config.model_name == "test-model"
            
        # Test with empty webhook URL
        with patch.object(mock_view, 'get_webhook_url', return_value=""), \
             patch.object(mock_view, 'show_error') as mock_error:
            
            result = controller._update_llm_client()
            assert result == False
            assert mock_error.called
            
        print("[OK] LLM configuration works with valid URL")
        print("[OK] LLM configuration fails with empty URL")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] LLM configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling methods."""
    print("\nTesting error handling...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        controller = SummarizerController(mock_view)
        
        # Test error handling
        with patch.object(mock_view, 'display_response'), \
             patch.object(mock_view, 'show_error'), \
             patch.object(mock_view, 'show_loading'), \
             patch.object(mock_view, 'set_status'):
            
            controller._on_error("Test error message")
            
            # Verify error display methods were called
            assert mock_view.display_response.called
            assert mock_view.show_error.called
            assert mock_view.show_loading.called
            
        print("[OK] Error handling works correctly")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_export_functionality():
    """Test export functionality."""
    print("\nTesting export functionality...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        controller = SummarizerController(mock_view)
        
        # Set some summary content
        controller.current_summary = "Test summary content"
        
        # Mock file dialog and file operations
        with patch('tkinter.filedialog.asksaveasfilename', return_value="/test/export.txt"), \
             patch('builtins.open', mock_open()) as mock_file:
            
            controller.handle_export_txt(manual_call=True)
            
            # Verify file was written
            mock_file.assert_called()
            
        print("[OK] Export functionality works")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Export functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_copy_functionality():
    """Test copy to clipboard functionality."""
    print("\nTesting copy functionality...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        controller = SummarizerController(mock_view)
        
        # Set response content
        with patch.object(mock_view, 'get_response_content', return_value="Test content"), \
             patch.object(mock_view, 'show_success') as mock_success:
            
            controller.handle_copy_clicked()
            
            # Verify success was shown
            assert mock_success.called
            
        print("[OK] Copy functionality works")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Copy functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transcriber_integration():
    """Test transcriber integration."""
    print("\nTesting transcriber integration...")
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        mock_view = SummarizerTab(notebook)
        
        # Create mock transcriber controller
        mock_transcriber = Mock()
        mock_transcriber.store_transcript = Mock()
        
        controller = SummarizerController(mock_view, transcriber_controller=mock_transcriber)
        
        # Test forwarding to transcriber
        controller.current_transcript = "Test transcript"
        controller.current_youtube_title = "Test Video"
        
        controller._forward_to_transcriber("Test transcript")
        
        # Verify transcriber method was called
        mock_transcriber.store_transcript.assert_called_with("Test transcript", "Test Video")
        
        print("[OK] Transcriber integration works")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAILED] Transcriber integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Mock file object for testing
def mock_open():
    """Mock open function for testing."""
    class MockFile:
        def __init__(self, path, mode='w'):
            self.path = path
            self.mode = mode
            self.content = ""
        
        def write(self, text):
            self.content += text
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    return MockFile


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing v9.3 SummarizerController Implementation")
    print("=" * 70)
    
    results = []
    
    # Run all test functions
    results.append(test_import())
    results.append(test_initialization())
    results.append(test_callback_wiring())
    results.append(test_file_handling())
    results.append(test_llm_configuration())
    results.append(test_error_handling())
    results.append(test_export_functionality())
    results.append(test_copy_functionality())
    results.append(test_transcriber_integration())
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"[SUCCESS] ALL TESTS PASSED ({passed}/{total})")
        print("\n[SUCCESS] v9.3 SummarizerController implementation is working correctly!")
        print("\nKey Features Verified:")
        print("- Import and initialization")
        print("- Callback wiring")
        print("- File handling workflow")
        print("- LLM configuration")
        print("- Error handling")
        print("- Export functionality")
        print("- Copy functionality")
        print("- Transcriber integration")
        return 0
    else:
        print(f"[FAILED] SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
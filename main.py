"""
Main entry point for n8n Summarizer application (v4.1)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber references)
- TranscriberTab ↔ TranscriberController
- BulkSummarizerTab ↔ BulkSummarizerController (Phase 4.1)

New in v4.1:
    - Full BulkSummarizerController implementation
    - Sequential file processing with threading
    - Progress tracking and real-time updates
    - Error handling with recovery
    - Output folder and file management
    - Support for .txt and .docx files

Version: 4.1
Updated: 2025-12-10 - Bulk Summarizer Phase 4.1 complete logic
"""
import tkinter as tk
from views.main_window import MainWindow
from controllers.file_controller import FileController
from controllers.youtube_summarizer_controller import YouTubeSummarizerController
from controllers.transcriber_controller import TranscriberController
from controllers.bulk_summarizer_controller import BulkSummarizerController
from utils.logger import logger
from config import APP_TITLE


def main():
    """
    Initialize and run the application.
    
    Creates:
    - MainWindow (views layer with all tabs)
    - FileController (coordinates FileTab + models)
    - TranscriberController (coordinates TranscriberTab + models)
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models)
    - BulkSummarizerController (Phase 4.1 - full bulk processing implementation)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v4.1")
    logger.info("=" * 50)
    
    try:
        # Create Tkinter root window
        root = tk.Tk()
        
        # Initialize main window (creates all tabs)
        window = MainWindow(root)
        
        # Initialize File Summarizer tab controller
        # Wires: FileTab UI ↔ FileController ↔ FileModel + N8NModel
        file_controller = FileController(window.file_tab)
        logger.info("FileController initialized")
        
        # Initialize Transcriber tab controller FIRST (so it's available for YouTube controller)
        # Wires: TranscriberTab UI ↔ TranscriberController ↔ TranscribeModel + N8NModel
        transcriber_controller = TranscriberController(window.transcriber_tab)
        logger.info("TranscriberController initialized")
        
        # Initialize YouTube Summarizer tab controller
        # Wires: YouTubeSummarizerTab UI ↔ YouTubeSummarizerController ↔ TranscribeModel + N8NModel
        # Pass BOTH transcriber_tab reference (for UI) AND transcriber_controller
        youtube_summarizer_controller = YouTubeSummarizerController(
            window.youtube_summarizer_tab,
            transcriber_tab=window.transcriber_tab,
            transcriber_controller=transcriber_controller
        )
        logger.info("YouTubeSummarizerController initialized")
        
        # Initialize Bulk Summarizer tab controller (Phase 4.1)
        # Wires: BulkSummarizerTab UI ↔ BulkSummarizerController ↔ N8NModel
        # Full implementation with:
        # - File discovery and validation
        # - Background threading
        # - Sequential processing
        # - Progress tracking
        # - Error handling
        # - Output management
        bulk_summarizer_controller = BulkSummarizerController(window.bulk_summarizer_tab)
        logger.info("BulkSummarizerController initialized (Phase 4.1 complete)")
        
        logger.info("Application ready")
        
        # Run GUI loop
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info(f"{APP_TITLE} closed")
        logger.info("=" * 50)


if __name__ == "__main__":
    main()

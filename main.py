"""
Main entry point for n8n Summarizer application (v4.0)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber references)
- TranscriberTab ↔ TranscriberController
- BulkSummarizerTab ↔ BulkSummarizerController (to be added in v4.1)

New in v4.0:
    - BulkSummarizerTab UI for bulk file processing (Phase 4.1 UI)
    - Ready for controller in v4.1

Version: 4.0
Updated: 2025-12-10 - Bulk Summarizer tab integration (Phase 4.1 UI)
"""
import tkinter as tk
from views.main_window import MainWindow
from controllers.file_controller import FileController
from controllers.youtube_summarizer_controller import YouTubeSummarizerController
from controllers.transcriber_controller import TranscriberController
from utils.logger import logger
from config import APP_TITLE


def main():
    """
    Initialize and run the application.
    
    Creates:
    - MainWindow (views layer with all tabs including Bulk Summarizer)
    - FileController (coordinates FileTab + models)
    - TranscriberController (coordinates TranscriberTab + models)
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models, with Transcriber references)
    
    Note: BulkSummarizerController will be added in v4.1
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v4.0")
    logger.info("=" * 50)
    
    try:
        # Create Tkinter root window
        root = tk.Tk()
        
        # Initialize main window (creates all tabs including Bulk Summarizer)
        window = MainWindow(root)
        
        # Initialize File Summarizer tab controller
        # Wires: FileTab UI ↔ FileController ↔ FileModel + N8NModel
        file_controller = FileController(window.file_tab)
        logger.info("FileController initialized")
        
        # Initialize Transcriber tab controller FIRST (so it's available for YouTube controller)
        # Wires: TranscriberTab UI ↔ TranscriberController ↔ TranscribeModel + N8NModel
        transcriber_controller = TranscriberController(window.transcriber_tab)
        logger.info("TranscriberController initialized")
        
        # Initialize YouTube Summarizer tab controller (v3.1)
        # Wires: YouTubeSummarizerTab UI ↔ YouTubeSummarizerController ↔ TranscribeModel + N8NModel
        # Pass BOTH transcriber_tab reference (for UI) AND transcriber_controller
        youtube_summarizer_controller = YouTubeSummarizerController(
            window.youtube_summarizer_tab,
            transcriber_tab=window.transcriber_tab,
            transcriber_controller=transcriber_controller
        )
        logger.info("YouTubeSummarizerController initialized")
        
        logger.info("Application ready")
        logger.info("Note: Bulk Summarizer tab UI ready (controller coming in v4.1)")
        
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

"""
Main entry point for n8n Summarizer application (v3.1)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber tab reference)
- TranscriberTab ↔ TranscriberController

New in v3.1:
    - YouTubeSummarizerController receives reference to TranscriberTab
    - Transcripts forwarded to Transcriber tab

Version: 3.1
Updated: 2025-12-07 - YouTube to Transcriber tab integration
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
    - MainWindow (views layer)
    - FileController (coordinates FileTab + models)
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models, with Transcriber tab reference)
    - TranscriberController (coordinates TranscriberTab + models)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v3.1")
    logger.info("=" * 50)
    
    try:
        # Create Tkinter root window
        root = tk.Tk()
        
        # Initialize main window (creates tabs)
        window = MainWindow(root)
        
        # Initialize File Summarizer tab controller
        # Wires: FileTab UI ↔ FileController ↔ FileModel + N8NModel
        file_controller = FileController(window.file_tab)
        logger.info("FileController initialized")
        
        # Initialize Transcriber tab controller FIRST (so it's available for YouTube controller)
        # Wires: TranscriberTab UI ↔ TranscriberController ↔ TranscribeModel + N8NModel
        transcriber_controller = TranscriberController(window.transcriber_tab)
        logger.info("TranscriberController initialized")
        
        # Initialize YouTube Summarizer tab controller (NEW in v3.1)
        # Wires: YouTubeSummarizerTab UI ↔ YouTubeSummarizerController ↔ TranscribeModel + N8NModel
        # Pass transcriber_tab reference so transcripts can be forwarded
        youtube_summarizer_controller = YouTubeSummarizerController(
            window.youtube_summarizer_tab,
            transcriber_tab=window.transcriber_tab  # NEW: Pass transcriber tab reference
        )
        logger.info("YouTubeSummarizerController initialized")
        
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

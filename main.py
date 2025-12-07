"""
Main entry point for n8n Summarizer application (v3.1.2)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber references)
- TranscriberTab ↔ TranscriberController

New in v3.1.2:
    - YouTubeSummarizerController receives references to both TranscriberTab AND TranscriberController
    - Transcripts forwarded to Transcriber tab view AND controller
    - Enables export in Transcriber tab

Version: 3.1.2
Updated: 2025-12-07 - YouTube to Transcriber tab integration + controller sharing
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
    - TranscriberController (coordinates TranscriberTab + models)
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models, with Transcriber references)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v3.1.2")
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
        # Pass BOTH transcriber_tab reference (for UI) AND transcriber_controller (NEW v3.1.2)
        youtube_summarizer_controller = YouTubeSummarizerController(
            window.youtube_summarizer_tab,
            transcriber_tab=window.transcriber_tab,  # v3.1 - Pass transcriber tab reference
            transcriber_controller=transcriber_controller  # NEW v3.1.2 - Pass controller reference
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

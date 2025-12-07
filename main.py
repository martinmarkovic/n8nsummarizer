"""
Main entry point for n8n Summarizer application (v3.0)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (NEW in v3.0)
- TranscriberTab ↔ TranscriberController

Version: 3.0
Updated: 2025-12-07 - YouTube Summarization tab integration
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
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models) [NEW]
    - TranscriberController (coordinates TranscriberTab + models)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v3.0")
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
        
        # Initialize YouTube Summarizer tab controller (NEW in v3.0)
        # Wires: YouTubeSummarizerTab UI ↔ YouTubeSummarizerController ↔ TranscribeModel + N8NModel
        youtube_summarizer_controller = YouTubeSummarizerController(window.youtube_summarizer_tab)
        logger.info("YouTubeSummarizerController initialized")
        
        # Initialize Transcriber tab controller (Local Files + YouTube URLs)
        # Wires: TranscriberTab UI ↔ TranscriberController ↔ TranscribeModel + N8NModel
        transcriber_controller = TranscriberController(window.transcriber_tab)
        logger.info("TranscriberController initialized")
        
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

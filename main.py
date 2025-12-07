"""
Main entry point for n8n Summarizer application (v2.2)

Wires up views and controllers:
- FileTab ↔ FileController
- TranscribeTab ↔ TranscribeController
"""
import tkinter as tk
from views.main_window import MainWindow
from controllers.file_controller import FileController
from controllers.transcribe_controller import TranscribeController
from utils.logger import logger
from config import APP_TITLE


def main():
    """
    Initialize and run the application.
    
    Creates:
    - MainWindow (views layer)
    - FileController (coordinates FileTab + models)
    - TranscribeController (coordinates TranscribeTab + models)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v2.2")
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
        
        # Initialize YouTube Transcriber tab controller
        # Wires: TranscribeTab UI ↔ TranscribeController ↔ TranscribeModel + N8NModel
        transcribe_controller = TranscribeController(window.transcribe_tab)
        logger.info("TranscribeController initialized")
        
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

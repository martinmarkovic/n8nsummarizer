"""
Main entry point for n8n Summarizer application (v5.0)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber references)
- TranscriberTab ↔ TranscriberController
- BulkSummarizerTab ↔ BulkSummarizerController
- BulkTranscriberTab ↔ BulkTranscriberController (NEW in v5.0)

New in v5.0:
    - Bulk Transcriber tab for folder-level media transcription
    - Media format selection (11 formats: mp4, mov, avi, mkv, webm, mp3, wav, m4a, flac, aac, wma)
    - Output format options (SRT, TXT, VTT, JSON)
    - Recursive subfolder scanning
    - Preference persistence in .env

Version: 5.0
Updated: 2026-01-06 - Phase 5.0 Bulk Transcription
"""
import tkinter as tk
from views.main_window import MainWindow
from controllers.file_controller import FileController
from controllers.youtube_summarizer_controller import YouTubeSummarizerController
from controllers.transcriber_controller import TranscriberController
from controllers.bulk_summarizer_controller import BulkSummarizerController
from controllers.bulk_transcriber_controller import BulkTranscriberController
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
    - BulkSummarizerController (coordinates BulkSummarizerTab + models)
    - BulkTranscriberController (coordinates BulkTranscriberTab + models, NEW in v5.0)
    
    Features (v5.0):
    - File summarization (txt, srt, docx, pdf)
    - YouTube summarization with transcription
    - Single file transcription (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
    - Bulk summarization with advanced options
    - Bulk transcription with media format selection and output formats
    - Recursive subfolder scanning for bulk operations
    - Preference persistence in .env
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v5.0")
    logger.info("=" * 50)
    
    try:
        # Create Tkinter root window
        root = tk.Tk()
        
        # Initialize main window (creates all tabs including Bulk Transcriber)
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
        
        # Initialize Bulk Summarizer tab controller (v4.2)
        # Wires: BulkSummarizerTab UI ↔ BulkSummarizerController
        # With advanced options: file types, output formats, custom location
        bulk_summarizer_controller = BulkSummarizerController(window.bulk_summarizer_tab)
        logger.info("BulkSummarizerController initialized (v4.2)")
        logger.info("Phase 4.2 features: Advanced options, preference persistence")
        
        # Initialize Bulk Transcriber tab controller (v5.0 NEW)
        # Wires: BulkTranscriberTab UI ↔ BulkTranscriberController
        # With media format selection, output formats, recursive scanning
        bulk_transcriber_controller = BulkTranscriberController(window.bulk_transcriber_tab)
        logger.info("BulkTranscriberController initialized (v5.0)")
        logger.info("Phase 5.0 features: Bulk media transcription, format selection, recursive scanning")
        
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

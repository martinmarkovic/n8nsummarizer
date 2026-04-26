"""
Main entry point for n8n Summarizer application (v8.2)

Wires up views and controllers:
- FileTab ↔ FileController
- YouTubeSummarizerTab ↔ YouTubeSummarizerController (with Transcriber references)
- TranscriberTab ↔ TranscriberController
- BulkSummarizerTab ↔ BulkSummarizerController
- BulkTranscriberTab ↔ BulkTranscriberController
- TranslationTab ↔ TranslationController
- DownloaderTab ↔ DownloaderController
- VideoSubtitlerTab ↔ VideoSubtitlerController

New in v8.1:
- Video Subtitler tab with download + transcription functionality
- Whisper integration for video transcription

Version: 8.1
Updated: 2026-04-26 - Video Subtitler feature
"""

import tkinter as tk
from views.main_window import MainWindow
from controllers.file_controller import FileController
from controllers.youtube_summarizer_controller import YouTubeSummarizerController
from controllers.transcriber_controller import TranscriberController
from controllers.bulk_summarizer_controller import BulkSummarizerController
from controllers.bulk_transcriber_controller import BulkTranscriberController
from controllers.translation_controller import TranslationController
from controllers.video_subtitler_controller import VideoSubtitlerController
from utils.logger import logger
from utils.settings_manager import SettingsManager
from config import APP_TITLE


def main():
    """
    Initialize and run the application.

    Creates:
    - SettingsManager (persistent user preferences)
    - MainWindow (views layer with all tabs)
    - FileController (coordinates FileTab + models)
    - TranscriberController (coordinates TranscriberTab + models)
    - YouTubeSummarizerController (coordinates YouTubeSummarizerTab + models)
    - BulkSummarizerController (coordinates BulkSummarizerTab + models)
    - BulkTranscriberController (coordinates BulkTranscriberTab + models)
    - TranslationController (coordinates TranslationTab + TranslationModel)
    - DownloaderTab with persistent settings

    Features (v6.3):
    - File summarization (txt, srt, docx, pdf)
    - YouTube summarization with transcription
    - Single file transcription (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
    - Bulk summarization with advanced options
    - Bulk transcription with media format selection and output formats
    - Translation tab (UI placeholder for future workflows)
    - YouTube video downloader
    - Recursive subfolder scanning for bulk operations
    - Preference persistence in .env (tab, path, quality)
    """
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE} v6.3")
    logger.info("=" * 50)

    try:
        # Initialize settings manager FIRST
        settings = SettingsManager()
        logger.info("SettingsManager initialized")

        # Create Tkinter root window
        root = tk.Tk()

        # Initialize main window (creates all tabs including Translation and Downloader)
        # Pass settings manager to main window
        window = MainWindow(root, settings)

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
            transcriber_controller=transcriber_controller,
        )
        logger.info("YouTubeSummarizerController initialized")

        # Initialize Bulk Summarizer tab controller
        # Wires: BulkSummarizerTab UI ↔ BulkSummarizerController
        # With advanced options: file types, output formats, custom location
        bulk_summarizer_controller = BulkSummarizerController(
            window.bulk_summarizer_tab
        )
        logger.info("BulkSummarizerController initialized")

        # Initialize Bulk Transcriber tab controller
        # Wires: BulkTranscriberTab UI ↔ BulkTranscriberController
        # With media format selection, output formats, recursive scanning
        bulk_transcriber_controller = BulkTranscriberController(
            window.bulk_transcriber_tab
        )
        logger.info("BulkTranscriberController initialized")

        # Initialize Translation tab controller
        # Wires: TranslationTab UI ↔ TranslationController ↔ TranslationModel
        translation_controller = TranslationController(window.translation_tab)
        logger.info("TranslationController initialized")

        # Initialize Video Subtitler tab controller
        # Wires: VideoSubtitlerTab UI ↔ VideoSubtitlerController ↔ VideoSubtitlerModel
        video_subtitler_controller = VideoSubtitlerController(window.video_subtitler_tab)
        logger.info("VideoSubtitlerController initialized")

        # Downloader tab controller already initialized in DownloaderTab.__init__
        # Now inject settings manager into it
        if hasattr(window, "downloader_tab") and window.downloader_tab.controller:
            window.downloader_tab.controller.set_settings_manager(settings)
            logger.info("DownloaderController configured with SettingsManager")

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

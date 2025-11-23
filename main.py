"""
Main entry point for Text File Scanner application
"""
import tkinter as tk
from views.main_window import MainWindow
from controllers.scanner_controller import ScannerController
from utils.logger import logger
from config import APP_TITLE


def main():
    """Initialize and run the application"""
    logger.info("=" * 50)
    logger.info(f"Starting {APP_TITLE}")
    logger.info("=" * 50)
    
    try:
        # Create Tkinter root window
        root = tk.Tk()
        
        # Initialize view
        view = MainWindow(root)
        
        # Initialize controller (connects view and models)
        controller = ScannerController(view)
        
        # Test n8n connection on startup
        controller.test_n8n_connection()
        
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
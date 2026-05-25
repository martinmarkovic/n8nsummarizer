"""
pyttsx3 TTS Engine - Offline text-to-speech functionality using pyttsx3.

This module provides simple offline/local text-to-speech capabilities
using the system's installed voices through pyttsx3.
"""

import threading
import logging
import pyttsx3

# Configure logging
logger = logging.getLogger(__name__)

# Global engine reference
_engine = None
_current_thread = None
_is_speaking = False


def is_available() -> bool:
    """
    Check if pyttsx3 is available and can be initialized.
    
    Returns:
        bool: True if pyttsx3 can be used, False otherwise
    """
    global _engine
    
    try:
        if _engine is None:
            # Try to initialize engine
            _engine = pyttsx3.init()
            logger.info("pyttsx3 engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize pyttsx3: {e}")
        _engine = None
        return False


def speak(text: str) -> None:
    """
    Speak the given text using pyttsx3.
    
    Args:
        text: Text to speak
        
    Notes:
        - Runs in a daemon thread to prevent UI freezing
        - Stops any currently playing speech before starting new speech
        - Ignores empty or whitespace-only text
        - Reinitializes engine for each speech to ensure clean state
    """
    global _current_thread, _is_speaking, _engine
    
    # Check if text is empty or invalid
    if not text or not text.strip():
        logger.warning("Cannot speak empty text")
        return
    
    # Ensure engine is available
    if not is_available():
        logger.warning("pyttsx3 not available")
        return

    logger.info(f"Speaking: {text[:50]}{'...' if len(text) > 50 else ''}")
    
    # Stop any currently playing speech and reset engine state
    stop()
    
    # Run speech in daemon thread
    def _speak_thread():
        global _is_speaking, _engine
        _is_speaking = True
        
        try:
            # Reinitialize engine to ensure clean state for each speech
            # This fixes issues when switching between multiple text boxes
            if _engine is not None:
                try:
                    _engine.endLoop()  # End any previous loops
                except:
                    pass  # Ignore errors
                
                try:
                    # Create fresh engine instance for reliable operation
                    _engine = pyttsx3.init()
                    logger.debug("Created fresh pyttsx3 engine instance")
                except Exception as init_error:
                    logger.error(f"Failed to reinitialize engine: {init_error}")
                    _is_speaking = False
                    return
            
            # Set up engine properties
            if _engine is not None:
                _engine.setProperty('rate', 180)  # Moderate speaking rate
                _engine.setProperty('volume', 0.9)  # Near maximum volume
                
                # Speak the text
                _engine.say(text)
                _engine.runAndWait()
                
                logger.info("Speech completed")
        except Exception as e:
            logger.error(f"Error during speech: {e}")
        finally:
            _is_speaking = False
    
    # Start as daemon thread
    _current_thread = threading.Thread(target=_speak_thread, daemon=True)
    _current_thread.start()


def stop() -> None:
    """
    Stop any currently playing speech.
    
    Always reset engine state to allow repeated speech, regardless of current speaking state.
    """
    global _engine, _is_speaking, _current_thread
    
    if _engine is not None:
        try:
            # Always stop the engine to reset its state for repeated use
            _engine.stop()
            logger.info("Speech stopped")
        except Exception as e:
            logger.error(f"Error stopping speech: {e}")
    
    _is_speaking = False
    _current_thread = None


def is_speaking() -> bool:
    """
    Check if speech is currently in progress.
    
    Returns:
        bool: True if speech is active, False otherwise
    """
    return _is_speaking


def get_available_voices() -> list:
    """
    Get list of available voices.
    
    Returns:
        list: Available voice names, or empty list if not available
    """
    if not is_available() or _engine is None:
        return []
    
    try:
        voices = _engine.getProperty('voices')
        return [voice.name for voice in voices]
    except Exception as e:
        logger.error(f"Failed to get available voices: {e}")
        return []
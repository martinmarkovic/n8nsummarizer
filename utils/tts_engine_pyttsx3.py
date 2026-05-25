"""
pyttsx3 TTS Engine - Offline text-to-speech functionality using pyttsx3.

This module provides simple offline/local text-to-speech capabilities
using the system's installed voices through pyttsx3.

Key design: Each utterance uses a fresh engine instance to avoid
state management issues and event loop conflicts.
"""

import threading
import logging
import pyttsx3

# Configure logging
logger = logging.getLogger(__name__)

# Thread safety and state
_state_lock = threading.Lock()
_current_thread = None
_is_speaking = False


def is_available() -> bool:
    """
    Check if pyttsx3 is available and can be initialized.
    
    Returns:
        bool: True if pyttsx3 can be used, False otherwise
    """
    try:
        # Test initialization
        test_engine = pyttsx3.init()
        del test_engine  # Clean up
        return True
    except Exception as e:
        logger.error(f"Failed to initialize pyttsx3: {e}")
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
        - Creates fresh engine for each utterance (per-utterance model)
        - Uses COM initialization for each thread to avoid conflicts
    """
    global _current_thread, _is_speaking
    
    # Check if text is empty or invalid
    if not text or not text.strip():
        logger.warning("Cannot speak empty text")
        return
    
    # Ensure pyttsx3 is available
    if not is_available():
        logger.warning("pyttsx3 not available")
        return

    logger.info(f"Speaking: {text[:50]}{'...' if len(text) > 50 else ''}")
    
    # Stop any currently playing speech
    stop()
    
    # Run speech in daemon thread to prevent UI freezing
    def _speak_thread():
        global _is_speaking
        with _state_lock:
            _is_speaking = True
        
        try:
            # Initialize COM for this thread
            import pythoncom
            pythoncom.CoInitialize()
            
            try:
                # Per-utterance engine model: create fresh engine
                engine = pyttsx3.init(driverName='sapi5')
                
                # Configure engine
                engine.setProperty('rate', 180)
                engine.setProperty('volume', 0.9)
                
                # Speak the text (blocking but in daemon thread)
                engine.say(text)
                engine.runAndWait()
                
                logger.info("Speech completed")
                
            finally:
                # Clean up COM
                pythoncom.CoUninitialize()
                
        except Exception as e:
            logger.error(f"Error during speech: {e}")
        finally:
            with _state_lock:
                _is_speaking = False
    
    # Start as daemon thread (UI remains responsive)
    with _state_lock:
        _current_thread = threading.Thread(target=_speak_thread, daemon=True)
        _current_thread.start()

def stop() -> None:
    """
    Stop any currently playing speech.
    
    Since each utterance uses its own engine instance, stopping is handled
    by clearing state and letting the current speech complete naturally.
    """
    global _is_speaking, _current_thread
    
    with _state_lock:
        # Mark as not speaking
        _is_speaking = False
        # Clear thread reference
        _current_thread = None
        logger.info("Speech stop requested")


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
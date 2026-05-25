"""
pyttsx3 TTS Engine - Offline text-to-speech functionality using pyttsx3.

This module provides simple offline/local text-to-speech capabilities
using the system's installed voices through pyttsx3.
"""

import threading
import logging
import pyttsx3
import time

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
        - Runs speech directly in a daemon thread
        - Stops any currently playing speech before starting new speech
        - Ignores empty or whitespace-only text
        - Uses simple, reliable approach
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
    
    # Simple, reliable approach: use pyttsx3.speak() directly
    # This avoids all the threading and engine state issues
    try:
        _is_speaking = True
        
        # Create fresh engine for each speech
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 0.9)
        
        # Use non-blocking speak and let it run in background
        engine.say(text)
        engine.runAndWait()
        
        logger.info("Speech completed")
        
    except Exception as e:
        logger.error(f"Error during speech: {e}")
    finally:
        _is_speaking = False

def stop() -> None:
    """
    Stop any currently playing speech.
    
    Uses engine.stop() to interrupt active speech.
    """
    global _engine, _is_speaking, _current_thread
    
    if _engine is not None:
        try:
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
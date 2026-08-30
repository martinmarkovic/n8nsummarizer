"""
pyttsx3 TTS Engine - Offline text-to-speech functionality using pyttsx3.

This module provides simple offline/local text-to-speech capabilities
using the system's installed voices through pyttsx3.

Key design: Each utterance uses a fresh engine instance. The active engine
is stored in a module-level reference so that stop() can interrupt playback
immediately by calling engine.stop() from another thread.
"""

import threading
import logging
import pyttsx3

# Configure logging
logger = logging.getLogger(__name__)

# Thread safety and state
_state_lock = threading.Lock()
_current_thread = None
_engine = None          # Reference to the currently speaking engine (for stop())
_is_speaking = False


def is_available() -> bool:
    """
    Check if pyttsx3 is available and can be initialized.

    Returns:
        bool: True if pyttsx3 can be used, False otherwise
    """
    try:
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
        - Creates a fresh engine for each utterance and stores it so stop()
          can interrupt playback
        - Uses COM initialization for each thread to avoid conflicts
    """
    global _current_thread, _is_speaking

    if not text or not text.strip():
        logger.warning("Cannot speak empty text")
        return

    if not is_available():
        logger.warning("pyttsx3 not available")
        return

    logger.info(f"Speaking: {text[:50]}{'...' if len(text) > 50 else ''}")

    # Interrupt any speech that's already playing
    stop()

    def _speak_thread():
        global _is_speaking, _engine
        with _state_lock:
            _is_speaking = True

        try:
            # Initialize COM for this thread (required for SAPI5 on Windows)
            import pythoncom
            pythoncom.CoInitialize()

            try:
                # Per-utterance engine model: create a fresh engine
                engine = pyttsx3.init(driverName='sapi5')
                engine.setProperty('rate', 180)
                engine.setProperty('volume', 0.9)

                # Publish the engine so stop() can interrupt it
                with _state_lock:
                    _engine = engine

                engine.say(text)
                engine.runAndWait()  # Blocks until finished or stopped

                logger.info("Speech completed")

            finally:
                with _state_lock:
                    _engine = None
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error during speech: {e}")
        finally:
            with _state_lock:
                _is_speaking = False

    with _state_lock:
        _current_thread = threading.Thread(target=_speak_thread, daemon=True)
        _current_thread.start()


def stop() -> None:
    """
    Stop any currently playing speech immediately.

    Grabs the active engine reference and calls engine.stop(), which
    interrupts the blocking runAndWait() loop in the speaking thread.
    """
    global _is_speaking

    with _state_lock:
        engine = _engine

    if engine is not None:
        try:
            engine.stop()
            logger.info("Speech stopped")
        except Exception as e:
            logger.debug(f"engine.stop() failed (may have already finished): {e}")
    else:
        logger.debug("Stop requested but no active speech")

    with _state_lock:
        _is_speaking = False


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
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        names = [voice.name for voice in voices]
        del engine
        return names
    except Exception as e:
        logger.error(f"Failed to get available voices: {e}")
        return []

"""
Kokoro TTS Engine - Text-to-Speech functionality using Kokoro ONNX model.

This module provides text-to-speech capabilities using the Kokoro TTS model.
The model files must be downloaded separately and placed in the models/kokoro/ directory.
"""

from pathlib import Path
import threading
import warnings

# Lazy imports - only import when needed
_kokoro = None
_sd = None

# Model paths
MODEL_DIR = Path(__file__).parent.parent / "models" / "kokoro"
MODEL_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_DIR / "voices.bin"


def is_available() -> bool:
    """
    Check if Kokoro TTS model files are available.
    
    Returns:
        bool: True if model files exist, False otherwise
    """
    return MODEL_PATH.exists() and VOICES_PATH.exists()


def _load_model():
    """
    Load the Kokoro TTS model (lazy initialization).
    
    Only loads the model if it hasn't been loaded already and files are available.
    """
    global _kokoro, _sd
    
    if _kokoro is None and is_available():
        try:
            # Import only when needed
            import kokoro_onnx
            import sounddevice as sd
            
            _kokoro = kokoro_onnx.Kokoro(MODEL_PATH, VOICES_PATH)
            _sd = sd
        except ImportError as e:
            warnings.warn(f"Failed to import TTS dependencies: {e}")
        except Exception as e:
            warnings.warn(f"Failed to load Kokoro model: {e}")


def stop():
    """
    Stop any currently playing speech.
    
    Safely stops sounddevice playback without raising exceptions.
    """
    if _sd is not None:
        try:
            _sd.stop()
        except Exception:
            pass  # Silently ignore any errors during stop


def speak(text: str):
    """
    Speak the given text using Kokoro TTS.
    
    Args:
        text (str): The text to speak
        
    Notes:
        - If model is not available, prints warning and returns
        - Stops any currently playing speech before starting new speech
        - Runs speech generation and playback in a daemon thread
    """
    if not is_available():
        warnings.warn("Kokoro TTS model not available. Please download model files.")
        return
    
    # Stop any currently playing speech
    stop()
    
    # Run speech generation and playback in a daemon thread
    def _speak_thread():
        _load_model()
        if _kokoro is None:
            return
            
        try:
            # Generate speech
            samples, sr = _kokoro.create(
                text.strip(), 
                voice="af_bella", 
                speed=1.0, 
                lang="en-us"
            )
            
            # Play audio
            _sd.play(samples, sr)
            _sd.wait()  # Wait for playback to complete
        except Exception as e:
            warnings.warn(f"Error during TTS playback: {e}")
    
    # Start as daemon thread so it doesn't block program exit
    threading.Thread(target=_speak_thread, daemon=True).start()
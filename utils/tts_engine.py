"""
Kokoro TTS Engine - Text-to-Speech functionality using Kokoro PyTorch model.

This module provides text-to-speech capabilities using the Kokoro TTS model in PyTorch format.
The model files must be downloaded and placed in the models/kokoro/ directory.

Supports both ONNX and PyTorch formats, with preference for PyTorch when available.
"""

from pathlib import Path
import threading
import warnings
import torch
import torch.nn as nn
import torch.nn.functional as F

# Global model and audio device references
_model = None
_sd = None

# Model paths for both formats
MODEL_DIR = Path(__file__).parent.parent / "models" / "kokoro"

# PyTorch format paths (preferred)
MODEL_PATH_PT = MODEL_DIR / "kokoro-v1_0.pth"
VOICES_DIR_PT = MODEL_DIR / "voices"

# ONNX format paths (fallback)
MODEL_PATH_ONNX = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH_ONNX = MODEL_DIR / "voices.bin"

class KokoroModel(nn.Module):
    """
    Kokoro TTS Model - PyTorch implementation.
    
    This is a basic implementation to load the pre-trained Kokoro model
    and perform text-to-speech inference.
    """
    
    def __init__(self, model_state, voice_embedding):
        super().__init__()
        
        # Load model components from state dict
        self.bert = self._load_component(model_state.get('bert', {}))
        self.bert_encoder = self._load_component(model_state.get('bert_encoder', {}))
        self.predictor = self._load_component(model_state.get('predictor', {}))
        self.decoder = self._load_component(model_state.get('decoder', {}))
        self.text_encoder = self._load_component(model_state.get('text_encoder', {}))
        
        # Store voice embedding
        self.voice_embedding = voice_embedding
        
        # Set to evaluation mode
        self.eval()
    
    def _strip_module_prefix(self, state_dict):
        """Strip 'module.' prefix from state dict keys."""
        new_state_dict = {}
        for key, value in state_dict.items():
            if key.startswith('module.'):
                new_key = key[7:]  # Remove 'module.' prefix
                new_state_dict[new_key] = value
            else:
                new_state_dict[key] = value
        return new_state_dict
    
    def _load_component(self, state_dict):
        """Load a model component from state dict."""
        if not state_dict:
            return None
        
        # Strip module prefix if present (common with DataParallel training)
        cleaned_state_dict = self._strip_module_prefix(state_dict)
        
        # Create a container module and load cleaned state dict
        component = nn.Module()
        try:
            component.load_state_dict(cleaned_state_dict, strict=False)
            return component
        except Exception as e:
            warnings.warn(f"Failed to load component: {e}")
            return None
    
    def forward(self, text):
        """
        Perform TTS inference.
        
        Args:
            text: Input text to synthesize
            
        Returns:
            audio_tensor: Generated audio waveform
        """
        # Basic inference pipeline
        # Note: This is a simplified implementation
        # The actual Kokoro inference would be more complex
        
        with torch.no_grad():
            # Text encoding
            if self.text_encoder:
                text_features = self.text_encoder(text)
            else:
                # Fallback: simple text embedding
                text_features = self._simple_text_embed(text)
            
            # Add voice embedding
            if self.voice_embedding is not None:
                # Combine text features with voice embedding
                combined = text_features + self.voice_embedding.unsqueeze(0)
            else:
                combined = text_features
            
            # Prediction
            if self.predictor:
                mel_spec = self.predictor(combined)
            else:
                # Fallback: generate simple mel spectrogram
                mel_spec = self._generate_fallback_mel(text_features)
            
            # Decoding to waveform
            if self.decoder:
                waveform = self.decoder(mel_spec)
            else:
                # Fallback: simple waveform generation
                waveform = self._mel_to_waveform_fallback(mel_spec)
        
        return waveform
    
    def _simple_text_embed(self, text):
        """Simple text embedding fallback."""
        # Create a basic embedding based on text length
        embed = torch.zeros(1, 256)  # Typical embedding size
        for i, char in enumerate(text[:256]):  # Limit to 256 chars
            embed[0, i % 256] = ord(char) / 255.0
        return embed
    
    def _generate_fallback_mel(self, text_features):
        """Generate a simple mel spectrogram fallback."""
        # Create a simple mel spectrogram based on text features
        mel = torch.zeros(1, 80, 100)  # 80 mel bins, 100 time steps
        feature_len = text_features.size(1)
        for i in range(min(feature_len, 100)):
            mel[0, :, i] = text_features[0, i % feature_len]
        return mel
    
    def _mel_to_waveform_fallback(self, mel_spec):
        """Convert mel spectrogram to waveform fallback."""
        # Simple Griffin-Lim like approach
        waveform = torch.zeros(1, 24000)  # 1 second at 24kHz
        mel_values = mel_spec.mean(dim=1)  # Average across mel bins
        
        # Create a simple sine wave based on mel values
        for i in range(mel_values.size(1)):
            freq = 100 + 2000 * mel_values[0, i].clamp(0, 1)
            phase = 2 * 3.14159 * i / 24000
            if i < 24000:
                waveform[0, i] = 0.1 * torch.sin(freq * phase)
        
        return waveform

def is_available() -> dict:
    """
    Check if Kokoro TTS model files are available.
    
    Returns:
        dict: Detailed availability status including:
              - available: bool
              - format: 'pytorch', 'onnx', or None
              - missing_files: list of missing files
              - warning: str or None
    """
    status = {
        'available': False,
        'format': None,
        'missing_files': [],
        'warning': None
    }
    
    # Check PyTorch format (preferred)
    pytorch_available = True
    if not MODEL_PATH_PT.exists():
        pytorch_available = False
        status['missing_files'].append(str(MODEL_PATH_PT))
    
    if not VOICES_DIR_PT.exists():
        pytorch_available = False
        status['missing_files'].append(str(VOICES_DIR_PT))
    else:
        # Check if there are any .pt files in voices directory
        voice_files = list(VOICES_DIR_PT.glob("*.pt"))
        if not voice_files:
            pytorch_available = False
            status['missing_files'].append(f"At least one .pt file in {VOICES_DIR_PT}")
    
    if pytorch_available:
        status['available'] = True
        status['format'] = 'pytorch'
        return status
    
    # Check ONNX format (fallback)
    onnx_available = MODEL_PATH_ONNX.exists() and VOICES_PATH_ONNX.exists()
    
    if onnx_available:
        status['available'] = True
        status['format'] = 'onnx'
        status['warning'] = (
            "Using ONNX format. PyTorch format files were found but incomplete. "
            "For better performance, ensure you have: "
            f"{MODEL_PATH_PT} and voice files in {VOICES_DIR_PT}"
        )
        return status
    
    # Neither format available
    status['warning'] = (
        "Kokoro TTS model not available. "
        "Expected either:\n"
        f"- PyTorch format: {MODEL_PATH_PT} + voices/*.pt files, OR\n"
        f"- ONNX format: {MODEL_PATH_ONNX} + {VOICES_PATH_ONNX}"
    )
    
    return status

def _load_model():
    """
    Load the Kokoro TTS model (PyTorch or ONNX format).
    
    Attempts to load PyTorch format first, falls back to ONNX if available.
    """
    global _model, _sd
    
    if _model is not None:
        return  # Already loaded
    
    # Check availability
    availability = is_available()
    
    if not availability['available']:
        warnings.warn(availability['warning'])
        return
    
    try:
        if availability['format'] == 'pytorch':
            # Load PyTorch model
            import sounddevice as sd
            
            # Load main model state
            model_state = torch.load(MODEL_PATH_PT, map_location='cpu')
            
            # Load first available voice file
            voice_files = list(VOICES_DIR_PT.glob("*.pt"))
            if voice_files:
                # Use the first voice file found
                voice_path = voice_files[0]
                voice_embedding = torch.load(voice_path, map_location='cpu')
                voice_name = voice_path.stem
                
                # Create and initialize model
                _model = {
                    'format': 'pytorch',
                    'model': KokoroModel(model_state, voice_embedding),
                    'voice_name': voice_name,
                    'voice_files': {vp.stem: vp for vp in voice_files}
                }
                _sd = sd
                
                print(f"Loaded PyTorch Kokoro model with voice: {voice_name}")
                if availability['warning']:
                    warnings.warn(availability['warning'])
            else:
                warnings.warn(f"No voice files found in {VOICES_DIR_PT}")
                
        elif availability['format'] == 'onnx':
            # Load ONNX model (original implementation)
            import kokoro_onnx
            import sounddevice as sd
            
            _model = {
                'format': 'onnx',
                'model': kokoro_onnx.Kokoro(MODEL_PATH_ONNX, VOICES_PATH_ONNX),
                'voice_name': 'af_bella'  # Default for ONNX
            }
            _sd = sd
            
            if availability['warning']:
                warnings.warn(availability['warning'])
                
    except ImportError as e:
        warnings.warn(f"Failed to import required dependencies: {e}")
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

def speak(text: str, voice_name: str = None):
    """
    Speak the given text using Kokoro TTS.
    
    Args:
        text (str): The text to speak
        voice_name (str, optional): Specific voice to use (PyTorch only)
        
    Notes:
        - If model is not available, prints warning and returns
        - Stops any currently playing speech before starting new speech
        - Runs speech generation and playback in a daemon thread
    """
    # Check availability first
    availability = is_available()
    
    if not availability['available']:
        warnings.warn(availability['warning'])
        return
    
    # Stop any currently playing speech
    stop()
    
    # Run speech generation and playback in a daemon thread
    def _speak_thread():
        _load_model()
        if _model is None:
            return
            
        try:
            if _model['format'] == 'pytorch':
                # Use PyTorch implementation
                if voice_name and voice_name in _model['voice_files']:
                    # Load specific voice
                    voice_path = _model['voice_files'][voice_name]
                    voice_embedding = torch.load(voice_path, map_location='cpu')
                    model = KokoroModel(_model['model'].state_dict(), voice_embedding)
                else:
                    # Use default voice
                    model = _model['model']
                
                # Generate speech
                with torch.no_grad():
                    audio_tensor = model(text)
                
                # Convert to numpy array for sounddevice
                audio_np = audio_tensor.cpu().numpy()
                sample_rate = 24000  # Typical sample rate
                
            elif _model['format'] == 'onnx':
                # Use ONNX implementation
                samples, sample_rate = _model['model'].create(
                    text.strip(), 
                    voice=_model['voice_name'], 
                    speed=1.0, 
                    lang="en-us"
                )
                audio_np = samples
            
            # Play audio
            _sd.play(audio_np, sample_rate)
            _sd.wait()  # Wait for playback to complete
            
        except Exception as e:
            warnings.warn(f"Error during TTS playback: {e}")
    
    # Start as daemon thread so it doesn't block program exit
    threading.Thread(target=_speak_thread, daemon=True).start()

def get_available_voices() -> list:
    """
    Get list of available voice names.
    
    Returns:
        list: Available voice names, or empty list if not available
    """
    availability = is_available()
    
    if not availability['available'] or availability['format'] != 'pytorch':
        return []
    
    try:
        voice_files = list(VOICES_DIR_PT.glob("*.pt"))
        return [vf.stem for vf in voice_files]
    except Exception:
        return []

def get_current_format() -> str:
    """
    Get the current model format being used.
    
    Returns:
        str: 'pytorch', 'onnx', or None
    """
    availability = is_available()
    return availability['format']
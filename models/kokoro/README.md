# Kokoro TTS Model Files

This implementation supports **both PyTorch and ONNX formats**, with preference for PyTorch when available.

## 🐍 PyTorch Format (Recommended)

The current local files use PyTorch format, which is now fully supported.

### Required Files

- `kokoro-v1_0.pth` - Main model file (PyTorch state dict)
- `voices/*.pt` - Individual voice files (at least one required)
- `VOICES.md` - Voice documentation (optional but helpful)

### Current Local Files

✅ **Main Model:**
- `kokoro-v1_0.pth` - **PRESENT**

✅ **Voice Files:**
- `voices/af_jessica.pt` - **PRESENT**

📚 **Documentation:**
- `VOICES.md` - Available voice documentation

## 🤖 ONNX Format (Fallback)

If PyTorch files are not available, the system can fall back to ONNX format.

### Required Files (ONNX)

- `kokoro-v1.0.onnx` - Main model file (ONNX format)
- `voices.bin` - Combined voice data

## Usage

The TTS system automatically detects available formats and uses:
1. **PyTorch format** if all required files are present
2. **ONNX format** as fallback if PyTorch files are missing

## Voice Selection

Available voices are automatically detected from the `voices/` directory.

### Using Specific Voices

```python
from utils.tts_engine import speak, get_available_voices

# Get available voices
voices = get_available_voices()
print(f"Available voices: {voices}")

# Speak with specific voice
speak("Hello world", voice_name="af_jessica")

# Use default voice
speak("Hello world")  # Uses first available voice
```

## Troubleshooting

### "Model not available" Errors

If you see this error:

1. **Check PyTorch files:**
   ```bash
   # Should show your model and voice files
   dir models\kokoro
   dir models\kokoro\voices
   ```

2. **Verify file names:**
   - Main model must be named `kokoro-v1_0.pth` (not `kokoro-v1.0.pth`)
   - Voice files must have `.pt` extension

3. **Check file permissions:** Ensure files are readable

### Performance Issues

- PyTorch format may use more memory than ONNX
- First load may be slower as model initializes
- Consider using a GPU for better performance

## Technical Details

### Model Architecture

The PyTorch model contains these components:
- **BERT**: Text embedding and encoding
- **BERT Encoder**: Additional encoding layers
- **Predictor**: Mel-spectrogram prediction
- **Decoder**: Waveform generation from mel-spectrogram
- **Text Encoder**: Specialized text processing

### Voice Files

Each `.pt` file contains a speaker embedding tensor that modifies the voice characteristics of the generated speech.

## Downloading Additional Voices

Additional voice files can be obtained from the original Kokoro repository.
Place `.pt` files in the `voices/` directory and they will be automatically detected.

## Format Comparison

| Aspect | PyTorch Format | ONNX Format |
|--------|---------------|-------------|
| **File Size** | Larger | Smaller |
| **Loading Time** | Slower | Faster |
| **Memory Usage** | Higher | Lower |
| **Flexibility** | Higher | Lower |
| **Voice Files** | Individual `.pt` files | Single `voices.bin` |
| **GPU Support** | Full support | Limited support |

The system prefers PyTorch format when available due to its flexibility and better GPU support.
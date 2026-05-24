# Kokoro TTS Model Files

Download the following files from https://huggingface.co/hexgrad/Kokoro-82M
and place them in this directory:

- `kokoro-v1.0.onnx`
- `voices.bin`

These files are ~300 MB total and are excluded from git.

## Installation Instructions

1. Visit https://huggingface.co/hexgrad/Kokoro-82M
2. Download both `kokoro-v1.0.onnx` and `voices.bin` files
3. Place them in this `models/kokoro/` directory
4. Restart the application

## Usage

Once the model files are in place, the "Read in Voice" option will be available in the right-click context menus of all output textboxes throughout the application.
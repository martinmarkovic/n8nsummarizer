#!/usr/bin/env python3
"""
Show the transcription commands used in n8n Summarizer
"""

import subprocess
import sys
from pathlib import Path

def show_transcribe_anything_command():
    """Show the transcribe-anything CLI command format"""
    print("=== TRANSCRIBE-ANYTHING CLI COMMAND ===")
    print("Used in: Transcriber Tab, Bulk Transcriber")
    print("Format:")
    print("  transcribe-anything <input_file> --device <device> --output_dir <output_dir>")
    print("\nExample:")
    print("  transcribe-anything video.mp4 --device cpu --output_dir C:\\output")
    print("\nDevice options: cpu, cuda, mps")

def show_whisper_direct_command():
    """Show the OpenAI Whisper direct usage"""
    print("\n=== OPENAI WHISPER DIRECT USAGE ===")
    print("Used in: Video Subtitler Tab")
    print("Python code:")
    print("  import whisper")
    print("  model = whisper.load_model('base', device='cpu')")
    print("  result = model.transcribe('video.mp4', fp16=False)")
    print("  # Convert segments to SRT format")

def check_transcribe_anything_available():
    """Check if transcribe-anything is available"""
    print("\n=== TRANScribe-ANYTHING AVAILABILITY ===")
    try:
        result = subprocess.run(["transcribe-anything", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("TRANSCRIBE-ANYTHING: AVAILABLE")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print("TRANSCRIBE-ANYTHING: ERROR")
            print(f"Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("TRANSCRIBE-ANYTHING: NOT FOUND")
        print("This is required for the Transcriber and Bulk Transcriber tabs")
        return False
    except Exception as e:
        print(f"✗ Error checking transcribe-anything: {e}")
        return False

def check_whisper_available():
    """Check if OpenAI Whisper is available"""
    print("\n=== OPENAI WHISPER AVAILABILITY ===")
    try:
        import whisper
        print("OPENAI WHISPER: AVAILABLE")
        print(f"Available models: {whisper.available_models()}")
        return True
    except ImportError:
        print("OPENAI WHISPER: NOT INSTALLED")
        print("Install with: pip install openai-whisper")
        return False
    except Exception as e:
        print(f"✗ Error checking Whisper: {e}")
        return False

def main():
    print("N8N SUMMARIZER TRANSCRIPTION COMMANDS")
    print("=" * 50)
    
    show_transcribe_anything_command()
    show_whisper_direct_command()
    
    check_transcribe_anything_available()
    check_whisper_available()
    
    print("\n=== USAGE NOTES ===")
    print("1. Transcriber Tab uses: transcribe-anything CLI")
    print("2. Video Subtitler Tab uses: OpenAI Whisper directly")
    print("3. Bulk Transcriber uses: transcribe-anything CLI")
    print("\nFor CPU-only systems, always use: --device cpu")

if __name__ == "__main__":
    main()
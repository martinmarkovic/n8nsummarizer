#!/usr/bin/env python3
"""
Prints the exact transcribe-anything command used in the transcriber tab
"""

import os
import subprocess
from pathlib import Path

def get_transcribe_command(input_path: str, output_dir: str, device: str = "cpu") -> list:
    """Return the exact command used by transcribe-anything"""
    cmd = [
        "transcribe-anything",
        input_path,
        "--device",
        device,
        "--output_dir",
        output_dir,
    ]
    return cmd

def main():
    # Example usage - replace with your actual file path
    input_file = "C:\\path\\to\\your\\video.mp4"
    output_dir = "C:\\path\\to\\output"
    device = "cpu"  # Use "cuda" if you have GPU
    
    cmd = get_transcribe_command(input_file, output_dir, device)
    
    print("\n=== TRANSCRIBE-ANYTHING COMMAND ===")
    print("Full command:")
    print(" ".join(cmd))
    
    print("\nIndividual arguments:")
    for i, arg in enumerate(cmd):
        print(f"  {i}: {repr(arg)}")
    
    print("\nTo run manually in CMD:")
    print(f"{' '.join(cmd)}")

if __name__ == "__main__":
    main()
"""Transcription package – extracted from models/transcribe_model.py.

This package provides the high-level :class:`TranscribeModel` and its
supporting helpers split into smaller, focused modules. The goal is to
keep the public API identical while making the implementation easier to
maintain and extend.
"""

from .model import TranscribeModel

__all__ = ["TranscribeModel"]

"""
Legacy shim for TranscribeModel during refactor.

This file now simply re-exports the new models.transcription package so that
existing imports

    from models.transcribe_model import TranscribeModel

continue to work without modification.
"""

from .transcription import TranscribeModel  # type: ignore[F401]

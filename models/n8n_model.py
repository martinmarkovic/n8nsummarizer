"""
Legacy shim for N8NModel during refactor.

This file now simply re-exports the new models.n8n package so that
existing imports

    from models.n8n_model import N8NModel

continue to work without modification.
"""

from .n8n import N8NModel  # type: ignore[F401]

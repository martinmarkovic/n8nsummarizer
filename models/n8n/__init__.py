"""
N8N Model - Business logic for n8n webhook communication with File Chunking Support

This package contains the N8NModel client and supporting components for
webhook communication, chunked processing and response parsing.

Submodules:
- client.py          → N8NModel public entry point
- chunking.py        → ContentChunker for file/content splitting
- response_parser.py → ResponseParser for extracting summaries
- config.py          → ChunkConfig and configuration helpers

The public API is exported from this package so existing imports like:
    from models.n8n_model import N8NModel

can be migrated to:
    from models.n8n import N8NModel

without exposing the internal submodule structure.
"""

from .client import N8NModel

__all__ = ["N8NModel"]

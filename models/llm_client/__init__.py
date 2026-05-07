"""LLM Client Package

OpenAI-compatible chat completions client for direct LLM integration.
Works with LM Studio, Ollama, vLLM, Jan, and any OpenAI-compatible server.
"""

from .client import LLMClient

__all__ = ["LLMClient"]
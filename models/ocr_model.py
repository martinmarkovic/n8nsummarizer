"""OCR Model - Picture to text via a local OpenAI-compatible vision model.

Sends an image plus an instruction prompt to a user-configured local server
(LM Studio, Unsloth llama-server, or Ollama) and returns the extracted text.

This reuses the same provider ids and endpoint conventions as
``models.llm_client`` but needs its own request path because the LLM client
only ever sends plain-string message content, whereas vision models require
the OpenAI "content parts" shape:

    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": [
            {"type": "text", "text": "..."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        ]},
    ]

Ollama's native /api/chat uses a different shape (a per-message ``images``
list of bare base64 strings), so the request is branched per provider.
"""

import base64
import mimetypes
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests

from utils.logger import logger


# Default instruction sent as the system prompt when the caller does not
# provide one. Kept deliberately plain so the model returns text only.
DEFAULT_OCR_PROMPT = (
    "You are an OCR engine. Extract all text visible in the image exactly as it "
    "appears, preserving line breaks and reading order. Return only the extracted "
    "text with no commentary, explanations, or formatting."
)

# Image types we are willing to inline. Anything else is rejected early with a
# clear message rather than sending a payload the server will reject.
_SUPPORTED_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class OCRModel:
    """Extract text from an image using a local vision-capable model."""

    def __init__(self, timeout: int = 180) -> None:
        """Initialize the model.

        Args:
            timeout: Per-request timeout in seconds. Vision models are slower
                than text, so this defaults higher than the LLM client.
        """
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(
        self,
        image_path: str,
        provider: str,
        base_url: str,
        model_name: str,
        prompt: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send an image to the configured provider and return extracted text.

        Args:
            image_path: Path to the image file on disk.
            provider: Provider id ('lmstudio', 'unsloth' or 'ollama-local').
            base_url: Base URL of the server (e.g. http://127.0.0.1:1234/v1).
            model_name: Vision model id to use.
            prompt: Optional instruction override; falls back to
                :data:`DEFAULT_OCR_PROMPT`.

        Returns:
            Tuple of (success, text, error_message). On success ``text`` holds
            the extracted text and ``error_message`` is None; on failure
            ``text`` is None and ``error_message`` explains why.
        """
        prompt = (prompt or "").strip() or DEFAULT_OCR_PROMPT

        if not base_url or not base_url.strip():
            return False, None, "Server base URL is not configured."
        if not model_name or not model_name.strip():
            return False, None, "No model selected. Test the connection and pick a model first."

        # Encode the image (also validates existence and type).
        ok, encoded, mime, encode_error = self._encode_image(image_path)
        if not ok:
            return False, None, encode_error

        provider_str = str(provider).strip().lower()

        try:
            endpoint, request_body = self._build_request(
                provider_str, base_url, model_name, prompt, encoded, mime
            )
        except ValueError as exc:
            return False, None, str(exc)

        logger.info(f"OCR request -> {endpoint} (provider={provider_str}, model={model_name})")

        try:
            response = requests.post(
                endpoint,
                json=request_body,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        except requests.exceptions.Timeout:
            error = f"OCR request timed out (>{self.timeout}s)."
            logger.error(error)
            return False, None, error
        except requests.exceptions.ConnectionError as exc:
            error = f"Cannot reach server at {base_url}: {exc}"
            logger.error(error)
            return False, None, error
        except requests.exceptions.RequestException as exc:
            error = f"OCR request failed: {exc}"
            logger.error(error)
            return False, None, error

        if response.status_code != 200:
            error = f"Server returned {response.status_code}: {response.text[:200]}"
            logger.error(error)
            return False, None, error

        return self._parse_response(provider_str, response)

    # ------------------------------------------------------------------
    # Request construction
    # ------------------------------------------------------------------

    def _build_request(
        self,
        provider_str: str,
        base_url: str,
        model_name: str,
        prompt: str,
        encoded_image: str,
        mime: str,
    ) -> Tuple[str, dict]:
        """Build the (endpoint, body) pair for the given provider.

        Raises:
            ValueError: If the provider id is not recognised.
        """
        parsed = urlparse(base_url.strip())
        origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

        if provider_str in {"lmstudio", "unsloth"}:
            # OpenAI-compatible vision chat.
            endpoint = f"{origin}/v1/chat/completions"
            body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{encoded_image}"
                                },
                            },
                        ],
                    },
                ],
                "stream": False,
            }
            return endpoint, body

        if provider_str == "ollama-local":
            # Ollama's native chat API carries images as a list of bare base64
            # strings on the message, not as OpenAI content parts.
            endpoint = f"{origin}/api/chat"
            body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": prompt, "images": [encoded_image]},
                ],
                "stream": False,
            }
            return endpoint, body

        raise ValueError(f"Unknown provider: {provider_str!r}")

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self, provider_str: str, response: requests.Response
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Extract the text content from a 200 response, per provider shape."""
        try:
            data = response.json()
        except ValueError as exc:
            error = f"Invalid JSON response: {exc}. Body: {response.text[:200]}"
            logger.error(error)
            return False, None, error

        text: Optional[str] = None

        if provider_str == "ollama-local":
            # {"message": {"role": "assistant", "content": "..."}}
            message = data.get("message")
            if isinstance(message, dict):
                text = message.get("content")
        else:
            # OpenAI chat: {"choices": [{"message": {"content": "..."}}]}
            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                text = None

        if text is None:
            error = f"Could not find text in response. Body: {response.text[:200]}"
            logger.error(error)
            return False, None, error

        # Strip <think>...</think> reasoning blocks some models emit.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

        logger.info(f"OCR extracted {len(text)} characters")
        return True, text, None

    # ------------------------------------------------------------------
    # Image handling
    # ------------------------------------------------------------------

    def _encode_image(
        self, image_path: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Read and base64-encode an image.

        Returns:
            Tuple of (success, encoded_base64, mime_type, error_message).
        """
        if not image_path:
            return False, None, None, "No image selected."

        path = Path(image_path)
        if not path.is_file():
            return False, None, None, f"Image not found: {image_path}"

        ext = path.suffix.lower()
        mime = _SUPPORTED_EXTENSIONS.get(ext)
        if mime is None:
            # Fall back to the system guess before giving up, so unusual but
            # valid extensions still work.
            guessed, _ = mimetypes.guess_type(str(path))
            if guessed and guessed.startswith("image/"):
                mime = guessed
            else:
                supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
                return (
                    False,
                    None,
                    None,
                    f"Unsupported image type '{ext or path.name}'. Supported: {supported}",
                )

        try:
            raw = path.read_bytes()
        except OSError as exc:
            return False, None, None, f"Could not read image: {exc}"

        if not raw:
            return False, None, None, "Image file is empty."

        encoded = base64.b64encode(raw).decode("ascii")
        return True, encoded, mime, None

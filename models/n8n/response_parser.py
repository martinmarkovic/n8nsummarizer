"""Response parsing helpers for N8NModel.

The original models/n8n_model.py contained fairly involved logic for
logging the full response and then extracting the most relevant
"summary" field. That logic is preserved here and factored into a
separate component so it can be reused and tested independently.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from utils.logger import logger


class ResponseParser:
    """Extract and combine summaries from n8n responses."""

    COMMON_KEYS: List[str] = [
        "summary",
        "summarization",
        "result",
        "output",
        "text",
        "content",
    ]

    def extract_summary(self, response_data: Any) -> Optional[str]:
        """Extract summary from an n8n response.

        Behaviour matches the original implementation:
        - Log the full response with type and keys
        - Try common keys (summary, result, output, text, content)
        - Treat empty/None as "no content" (return None)
        - Fallback to pretty-printed JSON or stringified representation
        """

        logger.debug("\n" + "=" * 70)
        logger.debug("EXTRACT_SUMMARY - Full N8N Response:")
        logger.debug(f"Response type: {type(response_data).__name__}")

        if isinstance(response_data, dict):
            logger.debug(f"Response keys: {list(response_data.keys())}")
            logger.debug("Response content (JSON):")
            for key, value in response_data.items():
                value_type = type(value).__name__
                if isinstance(value, str):
                    value_preview = value[:100] if len(value) > 100 else value
                    logger.debug(f"  {key}: ({value_type}) {value_preview}")
                elif isinstance(value, (dict, list)):
                    logger.debug(
                        f"  {key}: ({value_type}) {len(str(value))} chars"
                    )
                else:
                    logger.debug(f"  {key}: ({value_type}) {value}")
        elif isinstance(response_data, str):
            preview = (
                response_data[:200]
                if len(response_data) > 200
                else response_data
            )
            logger.debug(f"Response content (String): {preview}")
        else:
            logger.debug(f"Response content: {response_data}")

        logger.debug("=" * 70 + "\n")

        # Core extraction logic (unchanged)
        if response_data is None:
            logger.debug("Result: Response is None")
            return None

        if isinstance(response_data, str):
            if response_data.strip() == "":
                logger.debug("Result: Response is empty string")
                return None
            logger.debug(
                f"Result: Returning string response ({len(response_data)} chars)"
            )
            return response_data

        if isinstance(response_data, dict):
            logger.debug(f"Checking for common keys: {self.COMMON_KEYS}")

            for key in self.COMMON_KEYS:
                if key in response_data:
                    value = response_data[key]
                    logger.debug(
                        f"Found key '{key}' with type {type(value).__name__}"
                    )

                    if isinstance(value, str):
                        if value.strip():
                            logger.debug(
                                f"Result: Extracted from key '{key}' "
                                f"({len(value)} chars)"
                            )
                            return value
                        logger.debug(
                            f"  Key '{key}' is empty string, continuing"
                        )
                    elif isinstance(value, dict):
                        logger.debug(
                            f"Result: Found dict in key '{key}', returning as JSON"
                        )
                        return json.dumps(value, indent=2)
                    else:
                        str_value = str(value)
                        logger.debug(
                            f"Result: Found {type(value).__name__} in key '{key}', "
                            f"stringified ({len(str_value)} chars)"
                        )
                        return str_value

            if not response_data:
                logger.debug("Result: Response dict is empty")
                return None

            json_str = json.dumps(response_data, indent=2)
            logger.debug(
                "Result: No common keys found, returning full dict as JSON "
                f"({len(json_str)} chars)"
            )
            return json_str

        str_response = str(response_data)
        if str_response.strip():
            logger.debug(
                f"Result: Stringified {type(response_data).__name__} "
                f"({len(str_response)} chars)"
            )
            return str_response

        logger.debug("Result: Response is empty after stringification")
        return None

    def combine_summaries(
        self,
        file_name: str,
        summaries: List[str],
        total_chunks: int,
    ) -> str:
        """Combine partial summaries into a single output string.

        v4.6 user-facing change is preserved: the combined output is just
        the raw N8N/LM Studio content with **no** wrapper headers,
        section labels or footers. Summaries are simply separated by a
        blank line.
        """

        if not summaries:
            return ""

        if len(summaries) == 1:
            return summaries[0]

        combined = "\n\n".join(summaries)
        logger.info(
            f"Combined {len(summaries)} partial summaries into final output "
            "(no wrapper text)"
        )
        return combined

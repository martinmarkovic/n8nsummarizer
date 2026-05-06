"""LLM Client Configuration

Configuration dataclass for LLMClient with environment integration
and .env file persistence.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_TIMEOUT
from utils.logger import logger


@dataclass
class LLMClientConfig:
    """Configuration for LLMClient.
    
    Attributes:
        webhook_url: Base URL for OpenAI-compatible API endpoint
        model_name: Model name to use for completions
        timeout: Request timeout in seconds
        chunk_size_bytes: Maximum content size per API call (default: 400KB)
    """
    webhook_url: str
    model_name: str
    timeout: int
    chunk_size_bytes: int = 400_000  # 400KB default

    @classmethod
    def from_env(cls) -> 'LLMClientConfig':
        """Create configuration from environment variables.
        
        Reads LLM_WEBHOOK_URL, LLM_MODEL, and LLM_TIMEOUT from config.py
        which sources them from .env file.
        
        Returns:
            LLMClientConfig instance with values from environment
        """
        return cls(
            webhook_url=LLM_WEBHOOK_URL,
            model_name=LLM_MODEL,
            timeout=LLM_TIMEOUT
        )

    def save_to_env(self, webhook_url: str, model_name: str) -> bool:
        """Save configuration to .env file.
        
        Updates the .env file in project root with new values.
        Follows the same pattern as models/n8n/config.py ChunkConfig.save_webhook_to_env().
        
        Args:
            webhook_url: New webhook URL to save
            model_name: New model name to save
            
        Returns:
            True if save succeeded, False if failed
        """
        try:
            env_path = Path(__file__).parent.parent.parent / '.env'
            
            # Read existing .env content
            if env_path.exists():
                content = env_path.read_text(encoding='utf-8')
            else:
                content = ""
            
            # Update or add LLM configuration lines
            lines = content.split('\n')
            updated_lines = []
            
            # Track if we've updated existing lines
            webhook_updated = False
            model_updated = False
            
            for line in lines:
                if line.startswith('LLM_WEBHOOK_URL='):
                    updated_lines.append(f'LLM_WEBHOOK_URL={webhook_url}')
                    webhook_updated = True
                elif line.startswith('LLM_MODEL='):
                    updated_lines.append(f'LLM_MODEL={model_name}')
                    model_updated = True
                else:
                    # Keep comments and other lines unchanged
                    updated_lines.append(line)
            
            # Add missing lines if they weren't found
            if not webhook_updated:
                updated_lines.append(f'LLM_WEBHOOK_URL={webhook_url}')
            if not model_updated:
                updated_lines.append(f'LLM_MODEL={model_name}')
            
            # Write updated content
            env_path.write_text('\n'.join(updated_lines), encoding='utf-8')
            
            logger.info(f"Saved LLM configuration to .env: webhook_url={webhook_url}, model_name={model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save LLM configuration to .env: {e}", exc_info=True)
            return False
"""
LLM Model Discovery Service

Provides functionality to discover available models from different LLM providers
(LM Studio and Ollama) by querying their respective APIs.
"""

from typing import Literal, TypedDict, List, Tuple, Optional
import requests
from utils.logger import logger

# Type definitions
Provider = Literal["lmstudio", "ollama-local"]

class ModelOption(TypedDict):
    id: str
    label: str

# Provider configuration (mirrored from config.py for independence)
PROVIDER_CONFIG = {
    "lmstudio": {
        "default_base_url": "http://127.0.0.1:1234/v1",
        "list_models_path": "/models",
        "type": "openai"
    },
    "ollama-local": {
        "default_base_url": "http://localhost:11434/api",
        "list_models_path": "/tags", 
        "type": "ollama"
    }
}


def normalize_base_url(base_url: str) -> str:
    """
    Normalize base URL by removing trailing slashes.
    
    Args:
        base_url: The base URL to normalize
        
    Returns:
        Normalized base URL without trailing slash
    """
    base_url = base_url.strip()
    # Remove trailing slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    return base_url


def discover_models(provider: Provider, base_url: str) -> Tuple[List[ModelOption], str, Optional[str]]:
    """
    Discover available models from LLM provider.
    
    Args:
        provider: LLM provider ('lmstudio' or 'ollama-local')
        base_url: Base URL of the provider
        
    Returns:
        Tuple of (model_options, status, error_message)
        - model_options: List of available models with id and label
        - status: 'ok' on success, 'error' on failure
        - error_message: None if success, error message if failed
    """
    try:
        # Get provider config
        config = PROVIDER_CONFIG.get(provider)
        if not config:
            error_msg = f"Unknown provider: {provider}"
            logger.error(error_msg)
            return [], 'error', error_msg

        # Normalize base URL
        normalized_base_url = normalize_base_url(base_url)

        # Build full URL
        list_models_path = config['list_models_path']
        
        # Handle case where base_url might already include the path component
        if normalized_base_url.endswith(list_models_path.rstrip('/')):
            full_url = normalized_base_url
        else:
            full_url = f"{normalized_base_url}{list_models_path}"

        logger.info(f"Fetching models from {provider} at {full_url}")

        # Make request with timeout
        response = requests.get(
            full_url,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            error_msg = f"Failed to fetch models: HTTP {response.status_code}: {response.text[:100]}"
            logger.error(error_msg)
            return [], 'error', error_msg

        # Parse response based on provider
        if provider == 'lmstudio':
            # OpenAI-compatible response format
            # Expected: {"data": [{"id": "model-name", ...}]}
            try:
                data = response.json()
                models = data.get('data', [])
                model_options = [
                    {"id": model['id'], "label": model['id']}
                    for model in models
                    if 'id' in model
                ]
                logger.info(f"Discovered {len(model_options)} models from LM Studio")
                return model_options, 'ok', None
            except (ValueError, KeyError) as e:
                error_msg = f"Invalid response format from LM Studio: {str(e)}"
                logger.error(error_msg)
                return [], 'error', error_msg

        elif provider == 'ollama-local':
            # Ollama native API response format
            # Expected: {"models": [{"name": "model-name", "details": {...}}]}
            try:
                data = response.json()
                models = data.get('models', [])
                model_options = []
                for model in models:
                    name = model.get('name', '')
                    details = model.get('details', {})
                    parameter_size = details.get('parameter_size', '')
                    label = f"{name} ({parameter_size})" if parameter_size else name
                    model_options.append({"id": name, "label": label})
                logger.info(f"Discovered {len(model_options)} models from Ollama")
                return model_options, 'ok', None
            except (ValueError, KeyError) as e:
                error_msg = f"Invalid response format from Ollama: {str(e)}"
                logger.error(error_msg)
                return [], 'error', error_msg

    except requests.exceptions.Timeout:
        error_msg = "Connection timeout: Server did not respond within 10 seconds"
        logger.error(error_msg)
        return [], 'error', error_msg
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: Cannot reach server at {base_url}: {str(e)}"
        logger.error(error_msg)
        return [], 'error', error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return [], 'error', error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [], 'error', error_msg
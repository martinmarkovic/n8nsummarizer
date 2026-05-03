# n8n Webhook Communication

Handles HTTP communication with n8n workflows for summarization and processing tasks.

## Purpose

This subpackage provides:
- HTTP client for n8n webhook communication
- Request chunking for large content
- Response parsing and validation
- Error handling and retries

## Contents

| File | Purpose |
|------|---------|
| `__init__.py` | Exports public API (N8NClient, N8NChunking) |
| `client.py` | HTTP client implementation with retry logic |
| `chunking.py` | Large content splitting for API limits |
| `config.py` | n8n-specific configuration constants |
| `response_parser.py` | Response validation and parsing |

## Architecture

```
n8n/
├── client.py (HTTP communication)
├── chunking.py (content splitting)
├── config.py (configuration)
└── response_parser.py (response handling)
```

## Usage Example

```python
from models.n8n import N8NClient, N8NChunking

# Initialize client
client = N8NClient()

# Send request with automatic chunking
response = client.send_request(large_content)

# Process response
if response.success:
    print(f"Result: {response.data}")
else:
    print(f"Error: {response.error}")
```

## Chunking Strategy

Large content is automatically split into chunks to avoid API limits:

1. **Text Analysis**: Estimate token count
2. **Chunk Division**: Split into appropriate sizes
3. **Sequential Sending**: Process chunks in order
4. **Response Reconstruction**: Combine results

**Chunk Size**: Configurable via environment variables
- `N8N_CHUNK_SIZE`: Characters per chunk (default: 5000)
- `N8N_MAX_TOKENS`: Tokens per API call (default: 70000)

## Response Parsing

`response_parser.py` handles:
- JSON response validation
- Error code extraction
- Data structure normalization
- Empty response handling

## Error Handling

Comprehensive error management:
- Network timeouts (automatic retry)
- HTTP errors (status code handling)
- JSON parse errors (fallback strategies)
- Rate limiting (exponential backoff)

## Configuration

Configure via environment variables or `.env` file:

```env
# n8n Configuration
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_TIMEOUT=120
N8N_CHUNK_SIZE=5000
N8N_MAX_TOKENS=70000
```

## Integration

Used by controllers for n8n workflow execution:
- FileSummarizerController
- YouTubeSummarizerController
- BulkSummarizerController

## Extending

To add new n8n workflow support:

1. **Add Endpoint**: Update config.py with new URL
2. **Create Method**: Add method to client.py
3. **Update Parser**: Handle new response format
4. **Test**: Verify with mock n8n server

## Testing

Test with mock HTTP server:

```python
from unittest.mock import Mock
from models.n8n.client import N8NClient

# Mock HTTP response
mock_response = Mock(status_code=200)
mock_response.json.return_value = {"result": "success"}

# Test client
client = N8NClient()
# ... test specific methods
```
# Test Suite

Automated tests for Media SwissKnife application.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_file_scanner.py

# Run with verbose output
python -m pytest tests/ -v
```

## Current Test Coverage

### Existing Tests

| File | Coverage | Description |
|------|----------|-------------|
| `test_file_scanner.py` | FileReader model | Tests file reading, validation, and file info operations |
| `test_http_client.py` | HTTP client | Tests webhook communication and error handling |

**Test Scenarios Covered**:

#### test_file_scanner.py
- `test_read_valid_file`: Valid text file reading
- `test_read_nonexistent_file`: Non-existent file handling
- `test_read_empty_file`: Empty file validation
- `test_get_file_info`: File metadata extraction
- `test_clear`: File reader state reset

#### test_http_client.py
- HTTP request/response handling
- Timeout scenarios
- Error conditions
- Retry logic

### Coverage Gaps

**Missing Test Coverage** (areas needing tests):

| Component | Missing Coverage |
|-----------|------------------|
| **Controllers** | No unit tests for any controller |
| **Views** | No unit tests for any view |
| **Translation** | No tests for TranslationModel or TranslationService |
| **Downloader** | No tests for VideoDownloader or platform downloaders |
| **Integration** | No end-to-end workflow tests |

## Test Structure

```
tests/
├── __init__.py          # Test package initialization
├── test_file_scanner.py # File reading tests
├── test_http_client.py  # HTTP client tests
└── [future tests]      # Areas needing coverage
```

## Issues and Notes

### test_comprehensive_srt.py Location Issue

**Current Location**: Root directory
**Should Be**: `tests/test_comprehensive_srt.py`

This file tests SRT translation pipeline but is currently in the root directory. It should be moved to the tests/ directory for proper test organization.

**Action Required**: Move file and update imports

### SRT_TRANSLATION_FIX_SUMMARY.md Location Issue

**Current Location**: Root directory  
**Should Be**: `docs/SRT_TRANSLATION_FIX_SUMMARY.md`

This appears to be documentation rather than a test file and should be moved to the docs/ directory.

**Action Required**: Move to docs/ directory

## Writing New Tests

### Test Patterns

```python
import unittest
from models.file_reader import FileReader

class TestFileReader(unittest.TestCase):
    def setUp(self):
        """Setup test fixtures"""
        self.reader = FileReader()
        # Create test files

    def tearDown(self):
        """Cleanup after tests"""
        # Remove test files

    def test_specific_feature(self):
        """Test specific functionality"""
        # Arrange
        # Act
        # Assert
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
```

### Mocking Strategies

```python
from unittest.mock import Mock, patch
from controllers.file_controller import FileController

# Mock view
mock_view = Mock()
mock_view.get_content.return_value = "test content"

# Test controller
controller = FileController(mock_view)
result = controller.process_file()

# Verify view interactions
mock_view.show_result.assert_called_once()
```

## Test Priorities

### High Priority (Critical Paths)
1. **Controller Tests**: Verify workflow coordination
2. **Translation Tests**: Ensure translation pipeline works
3. **Downloader Tests**: Validate video download flows

### Medium Priority (Important Features)
1. **View Tests**: Verify UI component behavior
2. **Integration Tests**: End-to-end workflow validation
3. **Edge Case Tests**: Error conditions and recovery

### Low Priority (Nice to Have)
1. **Performance Tests**: Benchmark operations
2. **UI Automation Tests**: Full application testing
3. **Regression Tests**: Prevent future issues

## Test Data

Sample test files should be:
- Small and focused
- Committed to repository
- Located in `tests/data/` directory
- Cover edge cases

## Continuous Integration

Recommended CI setup:

```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: python -m pytest tests/ -v
```

## Improving Test Coverage

### Short-Term Goals
1. ✅ Document existing tests
2. ✅ Identify coverage gaps
3. ✅ Flag location issues
4. **Next**: Add controller tests
5. **Next**: Add translation tests

### Long-Term Goals
1. 80%+ code coverage
2. CI/CD integration
3. Automated regression testing
4. Performance benchmarking
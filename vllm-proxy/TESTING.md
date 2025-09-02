# Testing Guide for vLLM Proxy

## Setup

1. Create and activate a Python virtual environment:
```bash
python -m venv .venv
. .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r test-requirements.txt
```

## Running Tests

### Basic Usage

Use the provided test runner script:
```bash
./run_tests.sh
```

Or run manually:
```bash
. .venv/bin/activate
PYTHONPATH=src python -m pytest tests/ -v
```

Environment variables are automatically set by `tests/conftest.py`.

### Advanced Usage with Arguments


**Run a specific test file:**
```bash
./run_tests.sh tests/app/test_openai.py
# Expands to: PYTHONPATH=src python -m pytest tests/ -v tests/app/test_openai.py
```

**Run a specific test function:**
```bash
./run_tests.sh -k test_signature_default_algo
```

**Run tests with coverage report:**
```bash
./run_tests.sh --cov=app --cov-report=html
```

**Run tests in quiet mode:**
```bash
./run_tests.sh -q
```

**Stop on first failure with short traceback:**
```bash
./run_tests.sh -x --tb=short
```

**Exclude certain tests:**
```bash
./run_tests.sh -k "not test_quote"
```

**Run tests matching multiple patterns:**
```bash
./run_tests.sh -k "test_signature or test_stream"
```

## Key Testing Patterns

### 1. Mocking External Dependencies
```python
# Example from test_helpers.py
def setup_pynvml_mock():
    mock_pynvml = MagicMock()
    mock_pynvml.nvmlInit = MagicMock()
    mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
    sys.modules['pynvml'] = mock_pynvml
```

### 2. Replacing Modules Before Import
```python
# Example from test_openai.py
sys.modules['app.quote.quote'] = __import__('tests.app.mock_quote', fromlist=[''])
```

### 3. Mocking Cache Data
```python
# Properly formatted cache data for signature endpoint
cache_data = json.dumps({
    "text": test_data,
    "signature_ecdsa": ecdsa_quote.sign(test_data),
    "signing_address_ecdsa": ecdsa_quote.signing_address,
    "signature_ed25519": ed25519_quote.sign(test_data),
    "signing_address_ed25519": ed25519_quote.signing_address,
})
```

## CI/CD Integration

The test suite is designed to run in CI environments without special hardware:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    python -m venv .venv
    . .venv/bin/activate
    pip install -r src/requirements.txt
    pip install -r src/test-requirements.txt
    ./run_tests.sh
```
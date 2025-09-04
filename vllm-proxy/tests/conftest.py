import pytest
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set required environment variables before any imports
os.environ["MODEL_NAME"] = "test-model"
os.environ["VLLM_BASE_URL"] = "http://localhost:8001" 
os.environ["CHAT_CACHE_EXPIRATION"] = "1200"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_DB"] = "0"
os.environ["AUTH_TOKEN"] = "test-token"
os.environ["TOKEN"] = "test_token"
os.environ["SIGNING_METHOD"] = "ecdsa"

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test")
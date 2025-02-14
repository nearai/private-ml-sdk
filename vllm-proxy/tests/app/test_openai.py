from unittest.mock import patch, AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
import json

# Import and setup test environment before importing app
from tests.app.test_helpers import (
    setup_test_environment,
    TEST_AUTH_HEADER
)

# Setup all mocks before importing app
setup_test_environment()

# Now we can safely import app code
from app.main import app
from app.api.v1.openai import VLLM_URL
from app.quote.quote import quote, ED25519, ECDSA

client = TestClient(app)

async def yield_sse_response(data_list):
    for data in data_list:
        yield f"data: {json.dumps(data)}\n\n".encode('utf-8')

@pytest.mark.asyncio
@pytest.mark.respx
async def test_stream_chat_completions_success(respx_mock):
    # Test request data
    request_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }
    
    # Mock streaming response data
    chat_id = "chatcmpl-123"
    responses = [
        {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": 1677825464,
            "model": "test-model",
            "choices": [{"delta": {"role": "assistant"}, "index": 0, "finish_reason": None}]
        },
        {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": 1677825464,
            "model": "test-model",
            "choices": [{"delta": {"content": "Hello"}, "index": 0, "finish_reason": None}]
        },
        {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": 1677825464,
            "model": "test-model",
            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}]
        }
    ]

    # Setup RESPX mock
    route = respx_mock.post(VLLM_URL).mock(
        return_value=httpx.Response(
            200,
            stream=yield_sse_response(responses),
            headers={"Content-Type": "text/event-stream"}
        )
    )

    # Make request
    response = client.post(
        "/v1/chat/completions",
        json=request_data,
        headers={"Authorization": TEST_AUTH_HEADER}
    )
    
    # Verify response
    assert response.status_code == 200
    assert route.called

    # Collect all streaming responses
    chunks = []
    content = response.content.decode()
    for line in content.split('\n'):
        if line.startswith('data: '):
            chunk = json.loads(line.replace('data: ', ''))
            chunks.append(chunk)
    
    # Verify streaming response content
    assert len(chunks) == 3
    assert chunks[0]["id"] == chat_id
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[1]["choices"][0]["delta"]["content"] == "Hello"
    assert chunks[2]["choices"][0]["finish_reason"] == "stop"

@pytest.mark.asyncio
@pytest.mark.respx
async def test_stream_chat_completions_upstream_error(respx_mock):
    # Test request data
    request_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }
    
    # Setup RESPX mock with a 400 error response
    error_response = {
        "error": {
            "message": "Invalid request parameters",
            "type": "invalid_request_error",
            "code": 400
        }
    }
    route = respx_mock.post(VLLM_URL).mock(
        return_value=httpx.Response(
            400,
            json=error_response
        )
    )

    # Make request
    response = client.post(
        "/v1/chat/completions",
        json=request_data,
        headers={"Authorization": TEST_AUTH_HEADER}
    )
    
    # Verify response
    assert response.status_code == 400
    assert route.called
    
    # Verify error response content
    response_data = response.json()
    assert "error" in response_data
    assert response_data["error"]["message"] == "Invalid request parameters"
    assert response_data["error"]["type"] == "invalid_request_error"

@pytest.mark.asyncio
async def test_signature_default_algo():
    # Setup test data
    chat_id = "test-chat-123"
    test_data = "test request:response data"
    
    # Only mock the cache, use real quote object
    with patch('app.api.v1.openai.cache') as mock_cache:
        # Setup mock cache
        mock_cache.__contains__.return_value = True
        mock_cache.__getitem__.return_value = test_data

        # Make request
        response = client.get(
            f"/v1/signature/{chat_id}",
            headers={"Authorization": TEST_AUTH_HEADER}
        )

        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["text"] == test_data
        assert len(response_data["signature"]) > 0  # Real signature will have content
        assert response_data["signing_algo"] == ECDSA

@pytest.mark.asyncio
async def test_signature_explicit_algo():
    # Setup test data
    chat_id = "test-chat-123"
    test_data = "test request:response data"
    
    # Only mock the cache, use real quote object
    with patch('app.api.v1.openai.cache') as mock_cache:
        # Setup mock cache
        mock_cache.__contains__.return_value = True
        mock_cache.__getitem__.return_value = test_data

        # Make request with explicit algorithm
        explicit_algo = ECDSA if quote.signing_method == ED25519 else ED25519  # Use opposite of default
        response = client.get(
            f"/v1/signature/{chat_id}?signing_algo={explicit_algo}",
            headers={"Authorization": TEST_AUTH_HEADER}
        )

        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["text"] == test_data
        assert len(response_data["signature"]) > 0  # Real signature will have content
        assert response_data["signing_algo"] == explicit_algo

@pytest.mark.asyncio
async def test_signature_invalid_algo():
    chat_id = "test-chat-123"
    
    # Only mock the cache
    with patch('app.api.v1.openai.cache') as mock_cache:
        mock_cache.__contains__.return_value = True
        mock_cache.__getitem__.return_value = "test data"
    
        # Make request with invalid algorithm
        response = client.get(
            f"/v1/signature/{chat_id}?signing_algo=invalid-algo",
            headers={"Authorization": TEST_AUTH_HEADER}
        )

        # Verify error response
        assert response.status_code == 200  # FastAPI converts errors to 200 with error content
        response_data = response.json()
        assert "error" in response_data
        assert response_data["error"]["message"] == "Invalid signing algorithm. Must be 'ed25519' or 'ecdsa'"
        assert response_data["error"]["type"] == "invalid_signing_algo"

@pytest.mark.asyncio
async def test_signature_chat_not_found():
    chat_id = "nonexistent-chat"
    
    # Mock the cache to return False for contains check
    with patch('app.api.v1.openai.cache') as mock_cache:
        mock_cache.__contains__.return_value = False

        # Make request
        response = client.get(
            f"/v1/signature/{chat_id}",
            headers={"Authorization": TEST_AUTH_HEADER}
        )

        # Verify error response
        assert response.status_code == 200  # FastAPI converts errors to 200 with error content
        response_data = response.json()
        assert "error" in response_data
        assert response_data["error"]["message"] == "Chat id not found or expired"
        assert response_data["error"]["type"] == "chat_id_not_found"


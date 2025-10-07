import importlib
import json
import os
import sys
from collections import namedtuple
from hashlib import sha256
from unittest.mock import patch

import httpx
import respx
import pytest
from fastapi.testclient import TestClient

from tests.app.test_helpers import setup_test_environment, TEST_AUTH_HEADER
from tests.app.sample_dstack_data import NRAS_SAMPLE_RESPONSE
from verifiers.attestation_verifier import check_report_data, check_gpu

AppContext = namedtuple("AppContext", ["client", "vllm_url"])


@pytest.fixture(scope="module")
def app_context(request) -> AppContext:
    # Clear modules to ensure clean test environment
    for mod in ["app.main", "app.api", "app.api.v1", "app.api.v1.openai",
                "app.quote.quote", "pynvml"]:
        sys.modules.pop(mod, None)

    app_module = importlib.import_module("app.main")
    openai_module = importlib.import_module("app.api.v1.openai")

    # Enable no-GPU mode for testing
    importlib.import_module("app.quote.quote").NO_GPU_MODE = True

    return AppContext(TestClient(app_module.app), openai_module.VLLM_URL)

def test_chain_of_trust_end_to_end(app_context: AppContext):
    """Test the full chain: chat completion → signature → attestation verification."""
    client, vllm_url = app_context

    with respx.mock:
        # 1. Mock vLLM upstream and make chat completion request
        request_payload = {"model": "phala/deepseek-chat-v3-0324", "messages": [{"role": "user", "content": "Hello"}], "stream": False, "max_tokens": 4}
        upstream_payload = {"id": "chatcmpl-test-001", "object": "chat.completion", "choices": [{"message": {"role": "assistant", "content": "Hi there!"}, "index": 0, "finish_reason": "stop"}]}
        respx.mock.post(vllm_url).mock(return_value=httpx.Response(200, json=upstream_payload))

        response = client.post("/v1/chat/completions", json=request_payload, headers={"Authorization": TEST_AUTH_HEADER})
        assert response.status_code == 200
        chat_id = response.json()["id"]

    # 2. Calculate hashes for verification
    request_hash = sha256(json.dumps(request_payload, separators=(",", ":")).encode()).hexdigest()
    response_hash = sha256(response.content).hexdigest()

    # 3. Fetch and verify signature
    signature_json = client.get(f"/v1/signature/{chat_id}", headers={"Authorization": TEST_AUTH_HEADER}).json()
    assert signature_json["text"] == f"{request_hash}:{response_hash}"
    assert signature_json["signature"].startswith("0x")

    # 4. Fetch attestation
    nonce = "42" * 32
    attestation_json = client.get("/v1/attestation/report", params={"model": request_payload["model"], "nonce": nonce}, headers={"Authorization": TEST_AUTH_HEADER}).json()

    # 5. Verify attestation using verifier functions (same as end-users would use)
    report_result = check_report_data(attestation_json, nonce)
    assert all(report_result.values()), f"Report data verification failed: {report_result}"

    with patch("verifiers.attestation_verifier.fetch_nvidia_verification", return_value=NRAS_SAMPLE_RESPONSE):
        gpu_result = check_gpu(attestation_json, nonce)
        assert gpu_result["nonce_matches"] and gpu_result["verdict"], f"GPU verification failed: {gpu_result}"
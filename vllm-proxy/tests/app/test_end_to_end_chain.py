import json
import os

# Set GPU_NO_HW_MODE before importing app (NO_GPU_MODE is read at module import time)
os.environ["GPU_NO_HW_MODE"] = "1"

from hashlib import sha256
from unittest.mock import patch

import httpx
import respx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.app.test_helpers import TEST_AUTH_HEADER
from tests.app.sample_dstack_data import NRAS_SAMPLE_RESPONSE, NRAS_SAMPLE_PPCIE_RESPONSE
from verifiers.attestation_verifier import check_report_data, check_gpu, check_tdx_quote


@pytest.fixture(scope="module")
def client():
    if not os.path.exists('/var/run/dstack.sock'):
        pytest.skip("Not in a real TEE environment.")
    return TestClient(app)

@pytest.mark.parametrize("nras_response", [NRAS_SAMPLE_RESPONSE, NRAS_SAMPLE_PPCIE_RESPONSE])
def test_chain_of_trust_end_to_end(client, nras_response):
    """Test the full chain: chat completion → signature → attestation verification."""
    vllm_url = os.getenv("VLLM_BASE_URL", "http://vllm:8000") + "/v1/chat/completions"

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
    # First verify the TDX quote with Phala's verification API (real HTTP call)
    intel_result = check_tdx_quote(attestation_json)
    assert intel_result.get("quote", {}).get("verified"), "Intel TDX quote verification failed"

    # Verify report_data binds signing address and nonce
    report_result = check_report_data(attestation_json, nonce, intel_result)
    assert all(report_result.values()), f"Report data verification failed: {report_result}"

    # Verify GPU attestation
    with patch("verifiers.attestation_verifier.fetch_nvidia_verification", return_value=nras_response):
        gpu_result = check_gpu(attestation_json, nonce)
        assert gpu_result["nonce_matches"] and gpu_result["verdict"], f"GPU verification failed: {gpu_result}"

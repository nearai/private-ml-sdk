#!/usr/bin/env python3
"""Minimal guide for checking signed chat responses."""

import json
import os
import secrets
from hashlib import sha256

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

from verifiers.attestation_verifier import (
    check_report_data,
    check_gpu,
    check_tdx_quote,
    show_sigstore_provenance,
)

API_KEY = os.environ.get("API_KEY", "")
MODEL = "phala/deepseek-chat-v3-0324"
BASE_URL = "https://api.redpill.ai"


def sha256_text(text):
    """Calculate SHA256 hash of text."""
    return sha256(text.encode()).hexdigest()


def fetch_signature(chat_id):
    """Fetch signature for a chat completion."""
    url = f"{BASE_URL}/v1/signature/{chat_id}?model={MODEL}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    return requests.get(url, headers=headers, timeout=30).json()


def recover_signer(text, signature):
    """Recover Ethereum address from ECDSA signature."""
    message = encode_defunct(text=text)
    return Account.recover_message(message, signature=signature)


def fetch_attestation_for(signing_address):
    """Fetch attestation for a specific signing address."""
    nonce = secrets.token_hex(32)
    url = f"{BASE_URL}/v1/attestation/report?model={MODEL}&nonce={nonce}"
    report = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30).json()

    # Handle both single attestation and multi-node response formats
    if "all_attestations" in report:
        # Multi-node format: find the attestation matching the signing address
        attestation = next(
            item for item in report["all_attestations"]
            if item["signing_address"].lower() == signing_address.lower()
        )
    else:
        # Single attestation format: use the report directly
        attestation = report

    return attestation, nonce


def check_attestation(signing_address, attestation, nonce):
    """Verify attestation for a signing address (calls check_report_data, check_gpu, check_tdx_quote)."""
    intel_result = check_tdx_quote(attestation)
    check_report_data(attestation, nonce, intel_result)
    check_gpu(attestation, nonce)
    show_sigstore_provenance(attestation)


def verify_chat(chat_id, request_body, response_text, label):
    """Verify a chat completion signature and attestation."""
    request_hash = sha256_text(request_body)
    response_hash = sha256_text(response_text)

    print(f"\n--- {label} ---")
    signature_payload = fetch_signature(chat_id)
    print(json.dumps(signature_payload, indent=2))

    hashed_text = signature_payload["text"]
    request_hash_server, response_hash_server = hashed_text.split(":")
    print("Request hash matches:", request_hash == request_hash_server)
    print("Response hash matches:", response_hash == response_hash_server)

    signature = signature_payload["signature"]
    signing_address = signature_payload["signing_address"]
    recovered = recover_signer(hashed_text, signature)
    print("Signature valid:", recovered.lower() == signing_address.lower())

    attestation, nonce = fetch_attestation_for(signing_address)
    print("\nAttestation signer:", attestation["signing_address"])
    print("Attestation nonce:", nonce)
    check_attestation(signing_address, attestation, nonce)


def streaming_example():
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    body_json = json.dumps(body)
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        data=body_json,
        stream=True,
        timeout=30,
    )

    chat_id = None
    response_text = ""
    for chunk in response.iter_lines():
        line = chunk.decode()
        response_text += line + "\n"
        if line.startswith("data: {") and chat_id is None:
            chat_id = json.loads(line[6:])['id']

    verify_chat(chat_id, body_json, response_text, "Streaming example")


def non_streaming_example():
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "max_tokens": 1,
    }
    body_json = json.dumps(body)
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        data=body_json,
        timeout=30,
    )

    payload = response.json()
    chat_id = payload["id"]
    verify_chat(chat_id, body_json, response.text, "Non-streaming example")


def main():
    """Run example verification of streaming and non-streaming chat completions."""
    if not API_KEY:
        print("Error: API_KEY environment variable is required")
        print("Set it with: export API_KEY=your-api-key")
        return
    streaming_example()
    non_streaming_example()


if __name__ == "__main__":
    main()

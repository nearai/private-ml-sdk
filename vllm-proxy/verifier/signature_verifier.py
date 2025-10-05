#!/usr/bin/env python3
"""Minimal guide for checking signed chat responses."""

import base64
import json
import os
import secrets
from hashlib import sha256

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

API_KEY = os.environ["API_KEY"]
MODEL = "phala/deepseek-chat-v3-0324"
BASE_URL = "https://api.redpill.ai"
GPU_VERIFIER = "https://nras.attestation.nvidia.com/v3/attest/gpu"
INTEL_VERIFIER = "https://cloud-api.phala.network/api/v1/attestations/verify"
SIGSTORE_PROVENANCE = (
    "https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd"
)


def sha256_text(text):
    return sha256(text.encode()).hexdigest()


def fetch_signature(chat_id):
    url = f"{BASE_URL}/v1/signature/{chat_id}?model={MODEL}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    return requests.get(url, headers=headers, timeout=30).json()


def recover_signer(text, signature):
    message = encode_defunct(text=text)
    return Account.recover_message(message, signature=signature)


def fetch_attestation_for(signing_address):
    nonce = secrets.token_hex(32)
    url = f"{BASE_URL}/v1/attestation/report?model={MODEL}&nonce={nonce}"
    report = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30).json()
    nodes = report.get("all_attestations") or [report]
    node = next(item for item in nodes if item["signing_address"].lower() == signing_address.lower())
    return node, nonce


def check_attestation(signing_address, node, nonce):
    report_data = bytes.fromhex(node["report_data"])
    signing_key = bytes.fromhex(node["signing_key"])
    embedded_key = report_data[:32]
    embedded_nonce = report_data[32:]

    print("Report data binds signing key:", embedded_key == signing_key.ljust(32, b"\x00"))
    print("Report data embeds nonce:", embedded_nonce.hex() == nonce)

    derived_address = "0x" + node["signing_key"][-40:]
    print("Signing address derives from attested key:", derived_address.lower() == signing_address.lower())

    payload = json.loads(node["nvidia_payload"])
    print("GPU payload nonce matches:", payload["nonce"].lower() == nonce)
    body = requests.post(GPU_VERIFIER, data=node["nvidia_payload"], timeout=30).json()
    jwt_token = body[0][1]
    verdict = json.loads(base64url_payload(jwt_token))["x-nvidia-overall-att-result"]
    print("NVIDIA attestation verdict:", verdict)

    intel = requests.post(INTEL_VERIFIER, json={"hex": node["intel_quote"]}, timeout=30).json()
    print("Intel attestation accepted:", intel.get("verified"))
    if intel.get("message"):
        print("Intel verifier message:", intel["message"])

    compose = node["info"]["tcb_info"].get("app_compose")
    if compose:
        print("\nDocker compose manifest attested by the enclave:")
        print(compose)
        print("Compose sha256:", sha256(compose.encode()).hexdigest())


def base64url_payload(jwt_token):
    payload_b64 = jwt_token.split(".")[1]
    padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
    return base64.urlsafe_b64decode(padded).decode()


def verify_chat(chat_id, request_body, response_text, label):
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

    node, nonce = fetch_attestation_for(signing_address)
    print("\nAttestation signer:", node["signing_address"])
    print("Attestation nonce:", nonce)
    check_attestation(signing_address, node, nonce)

    print("\nReview Sigstore provenance for the container image:")
    print(SIGSTORE_PROVENANCE)


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
    streaming_example()
    non_streaming_example()


if __name__ == "__main__":
    main()

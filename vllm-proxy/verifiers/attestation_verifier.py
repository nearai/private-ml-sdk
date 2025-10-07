#!/usr/bin/env python3
"""Straightforward walkthrough for checking a Phala attestation."""

import argparse
import base64
import json
import secrets
from hashlib import sha256

import requests

API_BASE = "https://api.redpill.ai"
GPU_VERIFIER_API = "https://nras.attestation.nvidia.com/v3/attest/gpu"
PHALA_TDX_VERIFIER_API = "https://cloud-api.phala.network/api/v1/attestations/verify"
SIGSTORE_PROVENANCE = (
    "https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd"
)


def fetch_report(api_key, model, nonce):
    """Fetch attestation report from the API."""
    url = f"{API_BASE}/v1/attestation/report?model={model}&nonce={nonce}"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.get(url, headers=headers, timeout=30).json()


def fetch_nvidia_verification(payload):
    """Submit GPU evidence to NVIDIA NRAS for verification."""
    return requests.post(GPU_VERIFIER_API, json=payload, timeout=30).json()


def base64url_decode_jwt_payload(jwt_token):
    """Decode the payload section of a JWT token."""
    payload_b64 = jwt_token.split(".")[1]
    padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
    return base64.urlsafe_b64decode(padded).decode()


def check_report_data(attestation, nonce):
    """Verify that TDX report data binds the signing key and nonce.

    Returns dict with verification results.
    """
    report_data = bytes.fromhex(attestation["report_data"])
    signing_key = bytes.fromhex(attestation["signing_key"])
    embedded_key = report_data[:32]
    embedded_nonce = report_data[32:]

    binds_key = embedded_key == signing_key.ljust(32, b"\x00")
    embeds_nonce = embedded_nonce.hex() == nonce

    print("Report data binds signing key:", binds_key)
    print("Report data embeds nonce:", embeds_nonce)

    derived_address = "0x" + attestation["signing_key"][-40:]
    derives_address = derived_address.lower() == attestation["signing_address"].lower()
    print("Signing address derives from attested key:", derives_address)

    return {
        "binds_key": binds_key,
        "embeds_nonce": embeds_nonce,
        "derives_address": derives_address,
    }


def check_gpu(attestation, nonce):
    """Verify GPU attestation evidence via NVIDIA NRAS.

    Returns dict with verification results.
    """
    payload = json.loads(attestation["nvidia_payload"])
    nonce_matches = payload["nonce"].lower() == nonce
    print("GPU payload nonce matches:", nonce_matches)

    body = fetch_nvidia_verification(payload)

    jwt_token = body[0][1]
    verdict = json.loads(base64url_decode_jwt_payload(jwt_token))["x-nvidia-overall-att-result"]
    print("NVIDIA attestation verdict:", verdict)

    return {
        "nonce_matches": nonce_matches,
        "verdict": verdict,
    }


def check_tdx_quote(attestation):
    """Verify Intel TDX quote via Phala's verification service.

    Returns dict with verification results.
    """
    intel_result = requests.post(PHALA_TDX_VERIFIER_API, json={"hex": attestation["intel_quote"]}, timeout=30).json()
    payload = intel_result.get("quote") or {}
    verified = payload.get("verified")
    print("Intel TDX quote verified:", verified)
    message = payload.get("message") or intel_result.get("message")
    if message:
        print("Intel TDX verifier message:", message)

    return {
        "verified": verified,
        "message": message,
    }


def show_compose(attestation):
    """Display the Docker compose manifest from the attestation."""
    compose = attestation["info"]["tcb_info"].get("app_compose")
    if not compose:
        return
    print("\nDocker compose manifest attested by the enclave:")
    print(compose)

    compose_hash = sha256(compose.encode()).hexdigest()
    print("Compose sha256:", compose_hash)

    mr_config = attestation["info"].get("mr_config")
    if mr_config:
        print("mr_config:", mr_config)
        # mr_config should be 0x01 + sha256_hash
        expected_mr_config = "0x01" + compose_hash
        print("mr_config matches compose hash:", mr_config.lower() == expected_mr_config.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Phala Cloud TEE Attestation")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", default="phala/deepseek-chat-v3-0324")
    args = parser.parse_args()

    nonce = secrets.token_hex(32)
    report = fetch_report(args.api_key, args.model, nonce)

    # Handle both single attestation and multi-node response formats
    attestation = report.get("all_attestations", [report])[0] if report.get("all_attestations") else report

    print("\nSigning address:", attestation["signing_address"])
    print("Nonce:", nonce)

    print("\n🔐 TDX report data")
    check_report_data(attestation, nonce)

    print("\n🔐 GPU attestation")
    check_gpu(attestation, nonce)

    print("\n🔐 Intel TDX quote")
    check_tdx_quote(attestation)

    show_compose(attestation)

    print("\nReview Sigstore provenance for the container image:")
    print(SIGSTORE_PROVENANCE)


if __name__ == "__main__":
    main()

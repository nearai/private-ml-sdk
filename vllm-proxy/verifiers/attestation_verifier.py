#!/usr/bin/env python3
"""Straightforward walkthrough for checking a Phala attestation."""

import argparse
import base64
import json
import re
import secrets
from hashlib import sha256

import requests

API_BASE = "https://api.redpill.ai"
GPU_VERIFIER_API = "https://nras.attestation.nvidia.com/v3/attest/gpu"
PHALA_TDX_VERIFIER_API = "https://cloud-api.phala.network/api/v1/attestations/verify"
SIGSTORE_SEARCH_BASE = "https://search.sigstore.dev/?hash="


def fetch_report(model, nonce):
    """Fetch attestation report from the API."""
    url = f"{API_BASE}/v1/attestation/report?model={model}&nonce={nonce}"
    return requests.get(url, timeout=30).json()


def fetch_nvidia_verification(payload):
    """Submit GPU evidence to NVIDIA NRAS for verification."""
    return requests.post(GPU_VERIFIER_API, json=payload, timeout=30).json()


def base64url_decode_jwt_payload(jwt_token):
    """Decode the payload section of a JWT token."""
    payload_b64 = jwt_token.split(".")[1]
    padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
    return base64.urlsafe_b64decode(padded).decode()


def check_report_data(attestation, request_nonce, intel_result):
    """Verify that TDX report data binds the signing address and request nonce.

    Returns dict with verification results.
    """
    report_data_hex = intel_result["quote"]["body"]["reportdata"]
    report_data = bytes.fromhex(report_data_hex.removeprefix("0x"))
    signing_address = attestation["signing_address"]
    signing_algo = attestation.get("signing_algo", "").lower()

    # Parse signing address bytes based on algorithm
    if signing_algo == "ecdsa":
        # ECDSA: 20-byte Ethereum address (strip 0x prefix if present)
        addr_hex = signing_address[2:] if signing_address.startswith("0x") else signing_address
        signing_address_bytes = bytes.fromhex(addr_hex)
        if len(signing_address_bytes) != 20:
            raise ValueError(f"ECDSA address must be 20 bytes, got {len(signing_address_bytes)}")
    elif signing_algo == "ed25519":
        # Ed25519: 32-byte public key
        signing_address_bytes = bytes.fromhex(signing_address)
        if len(signing_address_bytes) != 32:
            raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(signing_address_bytes)}")
    else:
        raise ValueError(f"Unknown signing algorithm: {signing_algo}")

    embedded_address = report_data[:32]
    embedded_nonce = report_data[32:]

    binds_address = embedded_address == signing_address_bytes.ljust(32, b"\x00")
    embeds_nonce = embedded_nonce.hex() == request_nonce

    print("Signing algorithm:", signing_algo)
    print("Report data binds signing address:", binds_address)
    print("Report data embeds request nonce:", embeds_nonce)

    return {
        "binds_address": binds_address,
        "embeds_nonce": embeds_nonce,
    }


def check_gpu(attestation, request_nonce):
    """Verify GPU attestation evidence via NVIDIA NRAS.

    Returns dict with verification results.
    """
    payload = json.loads(attestation["nvidia_payload"])

    # Verify GPU uses the same request_nonce
    nonce_matches = payload["nonce"].lower() == request_nonce.lower()
    print("GPU payload nonce matches request_nonce:", nonce_matches)

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

    Returns the full intel_result including decoded quote data.
    """
    intel_result = requests.post(PHALA_TDX_VERIFIER_API, json={"hex": attestation["intel_quote"]}, timeout=30).json()
    payload = intel_result.get("quote") or {}
    verified = payload.get("verified")
    print("Intel TDX quote verified:", verified)
    message = payload.get("message") or intel_result.get("message")
    if message:
        print("Intel TDX verifier message:", message)

    return intel_result


def extract_sigstore_links(compose):
    """Extract all @sha256:xxx image digests and return Sigstore search links."""
    if not compose:
        return []

    # Match @sha256:hexdigest pattern in Docker compose
    pattern = r'@sha256:([0-9a-f]{64})'
    digests = re.findall(pattern, compose)

    return [f"{SIGSTORE_SEARCH_BASE}sha256:{digest}" for digest in digests]


def check_sigstore_links(links):
    """Check that Sigstore links are accessible (not 404)."""
    results = []
    for link in links:
        try:
            response = requests.head(link, timeout=10, allow_redirects=True)
            accessible = response.status_code < 400
            results.append((link, accessible, response.status_code))
        except requests.RequestException as e:
            results.append((link, False, str(e)))
    return results


def show_sigstore_provenance(attestation):
    """Extract and display Sigstore provenance links from attestation."""
    compose = attestation.get("info", {}).get("tcb_info", {}).get("app_compose")
    if not compose:
        return

    sigstore_links = extract_sigstore_links(compose)
    if not sigstore_links:
        return

    print("\n🔐 Sigstore provenance")
    print("Checking Sigstore accessibility for container images...")
    link_results = check_sigstore_links(sigstore_links)

    for link, accessible, status in link_results:
        if accessible:
            print(f"  ✓ {link} (HTTP {status})")
        else:
            print(f"  ✗ {link} (HTTP {status})")


def show_compose(attestation, intel_result):
    """Display the Docker compose manifest and verify against mr_config from verified quote."""
    compose = attestation["info"]["tcb_info"].get("app_compose")
    if not compose:
        return

    print("\nDocker compose manifest attested by the enclave:")
    print(compose)

    compose_hash = sha256(compose.encode()).hexdigest()
    print("Compose sha256:", compose_hash)

    mr_config = intel_result["quote"]["body"]["mrconfig"]
    print("mr_config (from verified quote):", mr_config)
    expected_mr_config = "0x01" + compose_hash
    print("mr_config matches compose hash:", mr_config.lower() == expected_mr_config.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Phala Cloud TEE Attestation")
    parser.add_argument("--model", default="phala/deepseek-chat-v3-0324")
    args = parser.parse_args()

    request_nonce = secrets.token_hex(32)
    report = fetch_report(args.model, request_nonce)

    # Handle both single attestation and multi-node response formats
    attestation = report.get("all_attestations", [report])[0] if report.get("all_attestations") else report

    print("\nSigning address:", attestation["signing_address"])
    print("Request nonce:", request_nonce)

    print("\n🔐 Intel TDX quote")
    intel_result = check_tdx_quote(attestation)

    print("\n🔐 TDX report data")
    check_report_data(attestation, request_nonce, intel_result)

    print("\n🔐 GPU attestation")
    check_gpu(attestation, request_nonce)

    show_compose(attestation, intel_result)
    show_sigstore_provenance(attestation)


if __name__ == "__main__":
    main()

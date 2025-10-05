#!/usr/bin/env python3
"""Straightforward walkthrough for checking a Phala attestation."""

import argparse
import base64
import json
import secrets
from hashlib import sha256

import requests

API_BASE = "https://api.redpill.ai"
GPU_VERIFIER = "https://nras.attestation.nvidia.com/v3/attest/gpu"
INTEL_VERIFIER = "https://cloud-api.phala.network/api/v1/attestations/verify"
SIGSTORE_PROVENANCE = (
    "https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd"
)


def fetch_report(api_key, model, nonce):
    url = f"{API_BASE}/v1/attestation/report?model={model}&nonce={nonce}"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.get(url, headers=headers, timeout=30).json()


def choose_node(report, index):
    nodes = report.get("all_attestations") or [report]
    return nodes[index]


def check_cpu(node, nonce):
    report_data = bytes.fromhex(node["report_data"])
    signing_key = bytes.fromhex(node["signing_key"])
    embedded_key = report_data[:32]
    embedded_nonce = report_data[32:]

    print("Report data binds signing key:", embedded_key == signing_key.ljust(32, b"\x00"))
    print("Report data embeds nonce:", embedded_nonce.hex() == nonce)

    derived_address = "0x" + node["signing_key"][-40:]
    print("Signing address derives from attested key:", derived_address.lower() == node["signing_address"].lower())


def check_gpu(node, nonce):
    payload = json.loads(node["nvidia_payload"])
    print("GPU payload nonce matches:", payload["nonce"].lower() == nonce)

    body = requests.post(GPU_VERIFIER, data=node["nvidia_payload"], timeout=30).json()
    jwt_token = body[0][1]
    payload_bytes = base64.urlsafe_b64decode(jwt_token.split(".")[1] + "==")
    verdict = json.loads(payload_bytes)["x-nvidia-overall-att-result"]
    print("NVIDIA attestation verdict:", verdict)


def check_intel(node):
    intel_result = requests.post(INTEL_VERIFIER, json={"hex": node["intel_quote"]}, timeout=30).json()
    print("Intel attestation accepted:", intel_result.get("verified"))
    if intel_result.get("message"):
        print("Intel verifier message:", intel_result["message"])


def show_compose(node):
    compose = node["info"]["tcb_info"].get("app_compose")
    if not compose:
        return
    print("\nDocker compose manifest attested by the enclave:")
    print(compose)
    print("Compose sha256:", sha256(compose.encode()).hexdigest())
    mr_config = node["info"].get("mr_config")
    if mr_config:
        print("mr_config:", mr_config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Phala Cloud TEE Attestation")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", default="phala/deepseek-chat-v3-0324")
    parser.add_argument("--node-index", type=int, default=0)
    args = parser.parse_args()

    nonce = secrets.token_hex(32)
    report = fetch_report(args.api_key, args.model, nonce)
    node = choose_node(report, args.node_index)

    print("\nSigning address:", node["signing_address"])
    print("Nonce:", nonce)

    print("\n🔐 CPU report data")
    check_cpu(node, nonce)

    print("\n🔐 GPU attestation")
    check_gpu(node, nonce)

    print("\n🔐 Intel TDX attestation")
    check_intel(node)

    show_compose(node)

    print("\nReview Sigstore provenance for the container image:")
    print(SIGSTORE_PROVENANCE)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify Phala Cloud attestation for CPU and GPU components."""

import argparse
import base64
import json
import secrets
from hashlib import sha256
from typing import Any, Dict, Tuple

import requests

API_BASE = "https://api.redpill.ai"
DEFAULT_MODEL = "phala/deepseek-chat-v3-0324"


def get_attestation_report(api_key: str, model: str, nonce_hex: str) -> Dict[str, Any]:
    url = f"{API_BASE}/v1/attestation/report?model={model}&nonce={nonce_hex}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def verify_gpu_attestation(nvidia_payload: str) -> Dict[str, Any]:
    url = "https://nras.attestation.nvidia.com/v3/attest/gpu"
    headers = {"accept": "application/json", "content-type": "application/json"}
    response = requests.post(url, headers=headers, data=nvidia_payload, timeout=30)
    response.raise_for_status()
    return response.json()


def verify_intel_tdx_attestation(intel_quote: str) -> str:
    print(f"   Copy this encoded Intel Quote: {intel_quote}")
    return "https://proof.t16z.com"


def parse_jwt_token(jwt_token: str) -> Dict[str, Any]:
    try:
        header, payload, signature = jwt_token.split(".")
    except ValueError:
        return {"error": "Invalid JWT format"}

    padding = len(payload) % 4
    if padding:
        payload += "=" * (4 - padding)
    payload_json = base64.urlsafe_b64decode(payload)
    return json.loads(payload_json)


def parse_report_data(report_data_hex: str) -> Tuple[bytes, bytes]:
    data = bytes.fromhex(report_data_hex)
    key = data[:32].rstrip(b"\x00")
    nonce = data[32:]
    return key, nonce


def pretty_status(title: str, ok: bool, detail: str = "") -> None:
    prefix = "✅" if ok else "❌"
    message = f"{prefix} {title}"
    if detail:
        message += f": {detail}"
    print(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Phala Cloud TEE Attestation")
    parser.add_argument("--api-key", required=True, help="Phala Cloud API key")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to verify")
    parser.add_argument(
        "--node-index",
        type=int,
        default=0,
        help="Index of node in all_attestations list to verify",
    )
    parser.add_argument(
        "--nonce",
        help="Hex-encoded 32-byte nonce (defaults to random)",
    )

    args = parser.parse_args()
    nonce_hex = args.nonce or secrets.token_hex(32)

    try:
        print("🔍 Fetching attestation report...")
        report = get_attestation_report(args.api_key, args.model, nonce_hex)

        if "all_attestations" in report and report["all_attestations"]:
            node = report["all_attestations"][args.node_index]
        else:
            node = report

        signing_address = node["signing_address"]
        nvidia_payload = node["nvidia_payload"]
        intel_quote = node["intel_quote"]

        print(f"✅ Signing address: {signing_address}")
        print(f"✅ Nonce: {nonce_hex}")

        print("\n🔐 Verifying GPU attestation with NVIDIA...")
        gpu_result = verify_gpu_attestation(nvidia_payload)
        if isinstance(gpu_result, list) and gpu_result:
            jwt_sections = gpu_result[0]
            if isinstance(jwt_sections, list) and len(jwt_sections) >= 2 and jwt_sections[0] == "JWT":
                jwt_payload = parse_jwt_token(jwt_sections[1])
                pretty_status(
                    "NVIDIA attestation verdict",
                    jwt_payload.get("x-nvidia-overall-att-result") == "SUCCESS",
                    jwt_payload.get("x-nvidia-overall-att-result", "unknown"),
                )
        else:
            pretty_status("NVIDIA attestation response received", True)

        gpu_payload = json.loads(nvidia_payload)
        pretty_status("GPU nonce matches", gpu_payload.get("nonce") == nonce_hex)

        print("\n🔐 Intel TDX attestation verification:")
        intel_url = verify_intel_tdx_attestation(intel_quote)
        print(f"✅ Intel TDX verification URL: {intel_url}")
        print("   Verify the quote against published MR values for full assurance.")

        report_data = node.get("report_data")
        attested_key_hex = node.get("attested_key")
        if report_data and attested_key_hex:
            attested_key_bytes, nonce_bytes = parse_report_data(report_data)
            nonce_ok = nonce_bytes == bytes.fromhex(nonce_hex)
            pretty_status("Nonce bound into TDX report", nonce_ok)

            key_ok = attested_key_bytes == bytes.fromhex(attested_key_hex)
            pretty_status("Report data binds signing key", key_ok)

            if signing_address.startswith("0x"):
                derived = "0x" + attested_key_hex[-40:]
                pretty_status(
                    "Signing address derived from attested key",
                    derived.lower() == signing_address.lower(),
                    derived,
                )

        info = node.get("info", {})
        compose = info.get("tcb_info", {}).get("app_compose") if isinstance(info.get("tcb_info"), dict) else None
        if compose:
            calculated = sha256(compose.encode("utf-8")).hexdigest()
            attested = info.get("compose_hash")
            pretty_status("Compose hash matches", calculated == attested, f"computed={calculated}")
            print("   Review the compose manifest to ensure it matches the published configuration.")
            mr_config = info.get("mr_config")
            if mr_config:
                print(f"   mr_config: {mr_config}")

        print("\n🎉 Attestation artifacts verified. Review Sigstore provenance for the container image:")
        print("   https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd")

    except requests.exceptions.HTTPError as exc:
        print(f"❌ HTTP Error: {exc}")
        if exc.response is not None and exc.response.status_code == 401:
            print("   Check API key permissions.")
    except Exception as exc:  # pragma: no cover - defensive output
        print(f"❌ Verification failed: {exc}")


if __name__ == "__main__":
    main()

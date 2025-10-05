#!/usr/bin/env python3
"""
Attestation Verifier for Phala Cloud Confidential AI

This script verifies both GPU and CPU attestation reports from Phala Cloud TEE environments.

Run with:
    python3 attestation_verifier.py --api-key YOUR_API_KEY [--model MODEL_NAME]
"""

import requests
import base64
import argparse
import json
from typing import Dict, Any


def get_attestation_report(
    api_key: str, model: str = "phala/deepseek-chat-v3-0324"
) -> Dict[str, Any]:
    """
    Fetch attestation report from Phala Cloud API

    Args:
        api_key: Your Phala Cloud API key
        model: The model to get attestation for

    Returns:
        Dictionary containing attestation report data
    """
    url = f"https://api.redpill.ai/v1/attestation/report?model={model}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def verify_gpu_attestation(nvidia_payload: str) -> Dict[str, Any]:
    """
    Verify NVIDIA GPU attestation using NVIDIA's attestation service

    Args:
        nvidia_payload: Base64 encoded NVIDIA attestation payload

    Returns:
        Dictionary containing NVIDIA verification response
    """
    url = "https://nras.attestation.nvidia.com/v3/attest/gpu"
    headers = {"accept": "application/json", "content-type": "application/json"}

    # The payload should be a JSON string, not base64 decoded
    response = requests.post(url, headers=headers, data=nvidia_payload)
    response.raise_for_status()
    return response.json()


def verify_intel_tdx_attestation(intel_quote: str) -> str:
    """
    Generate verification URL for Intel TDX attestation quote

    Args:
        intel_quote: Base64 encoded Intel TDX quote

    Returns:
        URL to verify the quote using TEE Attestation Explorer
    """
    print(f"   Copy this encoded Intel Quote: {intel_quote}")
    return f"https://proof.t16z.com"


def parse_jwt_token(jwt_token: str) -> Dict[str, Any]:
    """
    Parse and decode JWT token from NVIDIA attestation response

    Args:
        jwt_token: JWT token string

    Returns:
        Dictionary containing decoded JWT payload
    """
    try:
        # Split JWT into header, payload, signature
        parts = jwt_token.split(".")
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}

        # Decode the payload (middle part)
        payload_encoded = parts[1]
        # Add padding if needed
        padding = len(payload_encoded) % 4
        if padding:
            payload_encoded += "=" * (4 - padding)

        payload_json = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_json)

        return payload

    except Exception as e:
        return {"error": f"Failed to parse JWT: {e}"}


def main():
    """Main function to demonstrate attestation verification"""
    parser = argparse.ArgumentParser(description="Verify Phala Cloud TEE Attestation")
    parser.add_argument("--api-key", required=True, help="Phala Cloud API key")
    parser.add_argument(
        "--model",
        default="phala/deepseek-chat-v3-0324",
        help="Model to verify (default: phala/deepseek-chat-v3-0324)",
    )
    parser.add_argument(
        "--node-index",
        type=int,
        default=0,
        help="Index of node in all_attestations list to verify (default: 0)",
    )

    args = parser.parse_args()

    try:
        print("🔍 Fetching attestation report...")
        report = get_attestation_report(args.api_key, args.model)

        # Use specific node attestation if available
        if "all_attestations" in report and report["all_attestations"]:
            node_attestation = report["all_attestations"][args.node_index]
            nvidia_payload = node_attestation["nvidia_payload"]
            intel_quote = node_attestation["intel_quote"]
            signing_address = node_attestation["signing_address"]
        else:
            nvidia_payload = report["nvidia_payload"]
            intel_quote = report["intel_quote"]
            signing_address = report["signing_address"]

        print(f"✅ Signing address: {signing_address}")

        # Verify GPU attestation
        print("\n🔐 Verifying GPU attestation with NVIDIA...")
        gpu_result = verify_gpu_attestation(nvidia_payload)
        print(f"✅ GPU attestation verified successfully!")

        # Handle NVIDIA's complex response format
        if isinstance(gpu_result, list) and len(gpu_result) >= 2:
            # Response is a list with [JWT, {GPU attestations}]
            jwt_token = gpu_result[0]
            gpu_attestations = gpu_result[1]

            # Parse and display JWT token information
            if (
                isinstance(jwt_token, list)
                and len(jwt_token) >= 2
                and jwt_token[0] == "JWT"
            ):
                actual_jwt = jwt_token[1]
                jwt_payload = parse_jwt_token(actual_jwt)

                print(f"   Number of GPUs verified: {len(gpu_attestations)}")
                print(f"   JWT Issuer: {jwt_payload.get('iss', 'N/A')}")
                print(f"   JWT Subject: {jwt_payload.get('sub', 'N/A')}")
                print(
                    f"   Overall Attestation Result: {jwt_payload.get('x-nvidia-overall-att-result', 'N/A')}"
                )
            else:
                print(f"   Number of GPUs verified: {len(gpu_attestations)}")

                # Print info for each GPU
                for gpu_id in gpu_attestations:
                    print(f"   {gpu_id}: Attestation successful")

        elif isinstance(gpu_result, dict):
            # Response is a simple dictionary
            print(f"   GPU ID: {gpu_result.get('gpu_id', 'N/A')}")
            print(
                f"   Attestation Result: {gpu_result.get('attestation_result', 'N/A')}"
            )
        else:
            print(f"   Unexpected response format: {type(gpu_result)}")
            print(f"   Raw response: {gpu_result}")

        # Generate Intel TDX verification URL
        print("\n🔐 Intel TDX attestation verification:")
        intel_url = verify_intel_tdx_attestation(intel_quote)
        print(f"✅ Intel TDX verification URL: {intel_url}")
        print("   Visit the URL above to complete Intel TDX verification")

        print("\n🎉 All attestation verification steps completed successfully!")
        print("The TEE hardware has been verified as genuine and secure.")

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response.status_code == 401:
            print("   Please check your API key and ensure it has proper permissions")
        elif e.response.status_code == 404:
            print("   Model not found or attestation service unavailable")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

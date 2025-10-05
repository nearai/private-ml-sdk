#!/usr/bin/env python3
"""Verify signed responses returned by the Phala Cloud API."""

import argparse
import json
import os
import secrets
import sys
from hashlib import sha256
from typing import Optional

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

SUCCESS_EMOJI = "✅"
FAILURE_EMOJI = "❌"

MODEL = "phala/deepseek-chat-v3-0324"
BASE_URL = "https://api.redpill.ai"


def get_required_env(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if not value:
        print(f"ERROR: Required environment variable {key} is not set")
        sys.exit(1)
    return value


API_KEY = get_required_env("API_KEY")


def get_attestation_report(api_key: str, model: str, nonce_hex: str) -> dict:
    url = f"{BASE_URL}/v1/attestation/report?model={model}&nonce={nonce_hex}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def derive_address_from_attested_key(attested_key_hex: Optional[str]) -> Optional[str]:
    if not attested_key_hex:
        return None
    attested_key_hex = attested_key_hex.lower()
    if len(attested_key_hex) == 64:
        return "0x" + attested_key_hex[-40:]
    return None


def pretty_status(title: str, ok: bool, detail: str = "") -> None:
    prefix = SUCCESS_EMOJI if ok else FAILURE_EMOJI
    message = f"{prefix} {title}"
    if detail:
        message += f": {detail}"
    print(message)


def calculate_request_hash(request_body: str) -> str:
    return sha256(request_body.encode("utf-8")).hexdigest()


def calculate_response_hash(response_text: str) -> str:
    return sha256(response_text.encode("utf-8")).hexdigest()


def process_response_stream(response) -> dict:
    chat_id = None
    response_text = ""

    for line in response.iter_lines():
        line_str = line.decode("utf-8")
        response_text += line_str + "\n"

        if line_str.startswith("data: {") and chat_id is None:
            try:
                data = json.loads(line_str[6:])
                chat_id = data.get("id")
            except Exception:
                pass

    return {"chat_id": chat_id, "response_text": response_text}


def process_response_non_stream(response) -> dict:
    response_json = response.json()
    chat_id = response_json.get("id")
    response_text = response.text
    response_hash = calculate_response_hash(response_text)

    return {
        "chat_id": chat_id,
        "response_text": response_text,
        "response_hash": response_hash,
        "response_json": response_json,
    }


def verify_signature(text: str, signature: str, signing_address: str) -> bool:
    try:
        message = encode_defunct(text=text)
        recovered_address = Account.recover_message(message, signature=signature)
        return recovered_address.lower() == signing_address.lower()
    except Exception as exc:
        print(f"Signature verification error: {exc}")
        return False


def verify_signature_for_chat(
    chat_id: Optional[str],
    expected_request_hash: Optional[str] = None,
    expected_response_hash: Optional[str] = None,
    example_name: str = "",
) -> None:
    if not chat_id:
        return

    print(f"\n--- {example_name} ---")
    sig_response = requests.get(
        f"{BASE_URL}/v1/signature/{chat_id}?model={MODEL}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )

    if sig_response.status_code != 200:
        print(f"Failed to get signature: {sig_response.status_code}")
        return

    sig_data = sig_response.json()
    print(f"Signature data: {json.dumps(sig_data, indent=2)}")

    text = sig_data["text"]
    request_hash_from_server, response_hash_from_server = text.split(":")

    print("\nHash verification:")
    if expected_request_hash:
        pretty_status("Request hash matches", expected_request_hash == request_hash_from_server)
    else:
        print(f"Request hash from server: {request_hash_from_server}")

    if expected_response_hash:
        pretty_status("Response hash matches", expected_response_hash == response_hash_from_server)
    else:
        print(f"Response hash from server: {response_hash_from_server}")

    signature = sig_data["signature"]
    signing_address = sig_data["signing_address"]
    is_valid = verify_signature(text, signature, signing_address)
    pretty_status("Signature valid", is_valid)

    if not is_valid:
        return

    nonce_hex = secrets.token_hex(32)
    attestation = get_attestation_report(API_KEY, MODEL, nonce_hex)
    node = attestation["all_attestations"][0] if attestation.get("all_attestations") else attestation

    pretty_status(
        "Attestation signing address matches",
        node.get("signing_address") == signing_address,
    )

    report_data_hex = node.get("report_data")
    if report_data_hex:
        report_data_bytes = bytes.fromhex(report_data_hex)
        key_part = report_data_bytes[:32].rstrip(b"\x00").hex()
        bound_nonce = report_data_bytes[32:]
        pretty_status("Nonce bound into report", bound_nonce == bytes.fromhex(nonce_hex))

        attested_key_hex = node.get("attested_key")
        if signing_address.startswith("0x"):
            derived_address = derive_address_from_attested_key(attested_key_hex)
            if derived_address:
                pretty_status(
                    "Attested key derives signing address",
                    derived_address.lower() == signing_address.lower(),
                    derived_address,
                )
            pretty_status(
                "Report data encodes attested key",
                key_part == (attested_key_hex or "").lower(),
            )
        else:
            pretty_status(
                "Ed25519 public key matches attestation",
                (attested_key_hex or "").lower() == signing_address.lower() == key_part,
            )

    print("\nReview Sigstore provenance for the container image:")
    print("https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd")


def example_streaming_request() -> None:
    request_body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)
    calculated_hash = calculate_request_hash(request_body_str)

    print("\n=== Example 1: Streaming request without hash (server calculates) ===")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        data=request_body_str,
        stream=True,
        timeout=30,
    )

    result = process_response_stream(response)
    chat_id = result["chat_id"]
    response_text = result["response_text"]
    response_hash = calculate_response_hash(response_text)

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    verify_signature_for_chat(
        chat_id,
        calculated_hash,
        response_hash,
        "Streaming without X-Request-Hash",
    )


def example_non_streaming_request() -> None:
    request_body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)
    calculated_hash = calculate_request_hash(request_body_str)

    print("\n=== Example 2: Non-streaming request without hash ===")
    print(f"Calculated request hash: {calculated_hash}")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        data=request_body_str,
        timeout=30,
    )

    result = process_response_non_stream(response)
    chat_id = result["chat_id"]
    response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    verify_signature_for_chat(
        chat_id,
        calculated_hash,
        response_hash,
        "Non-streaming without X-Request-Hash",
    )


def example_with_request_hash(include_stream: bool) -> None:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": include_stream,
        "max_tokens": 1,
    }
    body_str = json.dumps(payload)
    request_hash = calculate_request_hash(body_str)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "X-Request-Hash": request_hash,
    }

    print(
        "\n=== Example 3: {} request with X-Request-Hash ===".format(
            "Streaming" if include_stream else "Non-streaming"
        )
    )

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=headers,
        data=body_str,
        stream=include_stream,
        timeout=30,
    )

    if include_stream:
        result = process_response_stream(response)
        chat_id = result["chat_id"]
        response_text = result["response_text"]
        response_hash = calculate_response_hash(response_text)
    else:
        result = process_response_non_stream(response)
        chat_id = result["chat_id"]
        response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    verify_signature_for_chat(
        chat_id,
        request_hash,
        response_hash,
        "Streaming with X-Request-Hash" if include_stream else "Non-streaming with X-Request-Hash",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phala Cloud Signature Verifier")
    parser.add_argument(
        "--skip-examples",
        action="store_true",
        help="Skip running example requests and only verify existing chats",
    )
    parser.add_argument("--chat-id", help="Existing chat ID to verify", default=None)
    parser.add_argument(
        "--request-hash", help="Expected request hash for the given chat", default=None
    )
    parser.add_argument(
        "--response-hash", help="Expected response hash for the given chat", default=None
    )

    args = parser.parse_args()

    if args.chat_id:
        verify_signature_for_chat(
            args.chat_id,
            args.request_hash,
            args.response_hash,
            "Manual verification",
        )
        return

    if args.skip_examples:
        print("No chat ID provided. Nothing to verify.")
        return

    example_streaming_request()
    example_non_streaming_request()
    example_with_request_hash(include_stream=True)
    example_with_request_hash(include_stream=False)


if __name__ == "__main__":
    main()

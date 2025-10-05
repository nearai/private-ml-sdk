#!/usr/bin/env python3
import json
import os
import requests
import sys

from typing import Optional
from hashlib import sha256
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3

# Emojis for status indication
SUCCESS_EMOJI = "✅"
FAILURE_EMOJI = "❌"

MODEL = "phala/deepseek-chat-v3-0324"
BASE_URL = "https://api.redpill.ai"


def get_required_env(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if not value:
        print(f"ERROR: Required environment variable {key} is not set")
        sys.exit(1)
    return value


API_KEY = get_required_env("API_KEY")


def calculate_request_hash(request_body: str):
    """Calculate SHA256 hash of request body string"""
    return sha256(request_body.encode("utf-8")).hexdigest()


def calculate_response_hash(response_text: str):
    """Calculate SHA256 hash of response body"""
    return sha256(response_text.encode("utf-8")).hexdigest()


def process_response_stream(response):
    """Process streaming response"""
    chat_id = None
    response_text = ""

    for line in response.iter_lines():
        line_str = line.decode("utf-8")
        response_text += line_str + "\n"

        # Extract chat ID from first chunk
        if line_str.startswith("data: {") and chat_id is None:
            try:
                data = json.loads(line_str[6:])  # Remove 'data: '
                chat_id = data.get("id")
            except:
                pass

    result = {"chat_id": chat_id, "response_text": response_text}
    print(">>>", result)

    return result


def process_response_non_stream(response):
    """Process non-streaming response and extract chat ID"""
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


def verify_signature(text, signature, signing_address):
    """Verify ECDSA signature against the given text and address"""
    try:
        message = encode_defunct(text=text)
        recovered_address = Account.recover_message(message, signature=signature)
        return recovered_address.lower() == signing_address.lower()
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


def verify_signature_for_chat(
    chat_id,
    expected_request_hash=None,
    expected_response_hash=None,
    example_name="",
):
    """Get and verify signature for a chat ID"""
    if not chat_id:
        return

    print(f"\n--- {example_name} ---")
    sig_response = requests.get(
        f"{BASE_URL}/v1/signature/{chat_id}?model={MODEL}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    if sig_response.status_code == 200:
        sig_data = sig_response.json()
        print(f"Signature data: {json.dumps(sig_data, indent=2)}")

        text = sig_data["text"]
        request_hash_from_server, response_hash_from_server = text.split(":")

        print(f"\nHash verification:")
        if expected_request_hash:
            request_match = expected_request_hash == request_hash_from_server
            request_emoji = SUCCESS_EMOJI if request_match else FAILURE_EMOJI
            print(f"{request_emoji} Request hash matches: {request_match}")
        else:
            print(f"Request hash from server: {request_hash_from_server}")

        if expected_response_hash:
            response_match = expected_response_hash == response_hash_from_server
            response_emoji = SUCCESS_EMOJI if response_match else FAILURE_EMOJI
            print(f"{response_emoji} Response hash matches: {response_match}")

        signature = sig_data["signature"]
        signing_address = sig_data["signing_address"]
        is_valid = verify_signature(text, signature, signing_address)
        emoji = SUCCESS_EMOJI if is_valid else FAILURE_EMOJI
        print(f"{emoji} Signature valid: {is_valid}")
    else:
        print(f"Failed to get signature: {sig_response.status_code}")


def example_streaming_request():
    """Example 1: Streaming request"""

    # Streaming request payload
    request_body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)
    calculated_hash = calculate_request_hash(request_body_str)

    print("\n=== Example 1: Streaming request without hash (let server calculate) ===")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        data=request_body_str,
        stream=True,
    )

    result = process_response_stream(response)
    chat_id = result["chat_id"]
    response_text = result["response_text"]
    response_hash = calculate_response_hash(response_text)

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    # Verify signature
    verify_signature_for_chat(
        chat_id,
        calculated_hash,
        response_hash,
        "Streaming without X-Request-Hash",
    )


def example_non_streaming_request():
    """Example 2: Non-streaming request"""

    # Non-streaming request payload
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
    )

    result = process_response_non_stream(response)
    chat_id = result["chat_id"]
    response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    # Verify signature
    verify_signature_for_chat(
        chat_id,
        calculated_hash,
        response_hash,
        "Non-streaming without X-Request-Hash",
    )


def main():
    example_streaming_request()
    example_non_streaming_request()


if __name__ == "__main__":
    main()

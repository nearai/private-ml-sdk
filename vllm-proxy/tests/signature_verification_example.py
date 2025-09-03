#!/usr/bin/env python3
import json
import os
import requests

from hashlib import sha256
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3

# Emojis for status indication
SUCCESS_EMOJI = "🟢"
FAILURE_EMOJI = "🔴"

# Global configuration
BASE_URL = os.getenv("VLLM_BASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def calculate_request_hash(request_body: str):
    """Calculate SHA256 hash of request body string"""
    return sha256(request_body.encode("utf-8")).hexdigest()


def calculate_response_hash(response_text: str):
    """Calculate SHA256 hash of response body"""
    return sha256(response_text.encode("utf-8")).hexdigest()


def process_response_stream(response, calculate_hash=False):
    """Process streaming response and optionally calculate hash"""
    chat_id = None
    response_text = ""
    h = sha256() if calculate_hash else None

    for line in response.iter_lines():
        if calculate_hash:
            # Add newline byte to restore line terminator removed by iter_lines() for accurate hash calculation
            h.update(line + b"\n")

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
    if calculate_hash:
        result["response_hash"] = h.hexdigest()

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
        f"{BASE_URL}/v1/signature/{chat_id}",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
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


def example_streaming_with_hash():
    """Example 1: Streaming request with pre-calculated hash"""

    # Streaming request payload
    request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)
    calculated_hash = calculate_request_hash(request_body_str)

    print("=== Example 1: Streaming request with pre-calculated hash ===")
    print(f"Calculated request hash: {calculated_hash}")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "X-Request-Hash": calculated_hash,
        },
        data=request_body_str,
        stream=True,
    )

    result = process_response_stream(response, calculate_hash=True)
    chat_id = result["chat_id"]
    response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    # Verify signature
    verify_signature_for_chat(
        chat_id,
        calculated_hash,
        response_hash,
        "Streaming with X-Request-Hash",
    )


def example_streaming_without_hash():
    """Example 2: Streaming request without hash header"""

    # Streaming request payload
    request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)

    print("\n=== Example 2: Streaming request without hash (let server calculate) ===")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}",
        },
        data=request_body_str,
        stream=True,
    )

    result = process_response_stream(response, calculate_hash=False)
    chat_id = result["chat_id"]
    response_text = result["response_text"]
    response_hash = calculate_response_hash(response_text)

    print(f"Chat ID: {chat_id}")

    # Verify signature
    verify_signature_for_chat(
        chat_id,
        None,
        response_hash,
        "Streaming without X-Request-Hash",
    )


def example_non_streaming_with_hash():
    """Example 3: Non-streaming request with pre-calculated hash"""

    # Non-streaming request payload
    request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)
    calculated_hash = calculate_request_hash(request_body_str)

    print("\n=== Example 3: Non-streaming request with pre-calculated hash ===")
    print(f"Calculated request hash: {calculated_hash}")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "X-Request-Hash": calculated_hash,
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
        "Non-streaming with X-Request-Hash",
    )


def example_non_streaming_without_hash():
    """Example 4: Non-streaming request without hash header"""

    # Non-streaming request payload
    request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "max_tokens": 1,
    }
    request_body_str = json.dumps(request_body)

    print("\n=== Example 4: Non-streaming request without hash ===")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}",
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
        None,
        response_hash,
        "Non-streaming without X-Request-Hash",
    )


def main():
    example_streaming_with_hash()
    example_streaming_without_hash()
    example_non_streaming_with_hash()
    example_non_streaming_without_hash()


if __name__ == "__main__":
    main()

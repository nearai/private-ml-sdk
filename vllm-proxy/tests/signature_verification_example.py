#!/usr/bin/env python3
import json
import os
import requests

from hashlib import sha256
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3


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
    base_url,
    auth_token,
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
        f"{base_url}/v1/signature/{chat_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    if sig_response.status_code == 200:
        sig_data = sig_response.json()
        print(f"Signature data: {json.dumps(sig_data, indent=2)}")

        text = sig_data["text"]
        request_hash_from_server, response_hash_from_server = text.split(":")

        print(f"\nHash verification:")
        if expected_request_hash:
            print(
                f"Request hash matches: {expected_request_hash == request_hash_from_server}"
            )
        else:
            print(f"Request hash from server: {request_hash_from_server}")

        if expected_response_hash:
            print(
                f"Response hash matches: {expected_response_hash == response_hash_from_server}"
            )

        signature = sig_data["signature"]
        signing_address = sig_data["signing_address"]
        is_valid = verify_signature(text, signature, signing_address)
        print(f"Signature valid: {is_valid}")
    else:
        print(f"Failed to get signature: {sig_response.status_code}")


def example_streaming_with_hash(
    base_url, auth_token, request_body_str, calculated_hash
):
    """Example 1: Streaming request with pre-calculated hash"""
    print("=== Example 1: Streaming request with pre-calculated hash ===")
    print(f"Calculated request hash: {calculated_hash}")

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
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

    return chat_id, response_hash


def example_streaming_without_hash(base_url, auth_token, request_body_str):
    """Example 2: Streaming request without hash header"""
    print("\n=== Example 2: Streaming request without hash (let server calculate) ===")

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
        data=request_body_str,
        stream=True,
    )

    result = process_response_stream(response, calculate_hash=False)
    chat_id = result["chat_id"]
    response_text = result["response_text"]
    response_hash = calculate_response_hash(response_text)

    print(f"Chat ID: {chat_id}")

    return chat_id, response_hash


def example_non_streaming_with_hash(
    base_url, auth_token, request_body_str, calculated_hash
):
    """Example 3: Non-streaming request with pre-calculated hash"""
    print("\n=== Example 3: Non-streaming request with pre-calculated hash ===")
    print(f"Calculated request hash: {calculated_hash}")

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
            "X-Request-Hash": calculated_hash,
        },
        data=request_body_str,
    )

    result = process_response_non_stream(response)
    chat_id = result["chat_id"]
    response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    return chat_id, response_hash


def example_non_streaming_without_hash(base_url, auth_token, request_body_str):
    """Example 4: Non-streaming request without hash header"""
    print("\n=== Example 4: Non-streaming request without hash ===")

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
        data=request_body_str,
    )

    result = process_response_non_stream(response)
    chat_id = result["chat_id"]
    response_hash = result["response_hash"]

    print(f"Chat ID: {chat_id}")
    print(f"Calculated response hash: {response_hash}")

    return chat_id, response_hash


def main():
    base_url = os.getenv("VLLM_BASE_URL")
    auth_token = os.getenv("AUTH_TOKEN")

    # Streaming request payload
    stream_request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "max_tokens": 1,
    }
    stream_request_str = json.dumps(
        stream_request_body, separators=(",", ":"), sort_keys=True
    )
    stream_calculated_hash = calculate_request_hash(stream_request_str)

    # Non-streaming request payload
    non_stream_request_body = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "max_tokens": 1,
    }
    non_stream_request_str = json.dumps(
        non_stream_request_body, separators=(",", ":"), sort_keys=True
    )
    non_stream_calculated_hash = calculate_request_hash(non_stream_request_str)

    # Run all four examples
    chat_id1, response_hash1 = example_streaming_with_hash(
        base_url, auth_token, stream_request_str, stream_calculated_hash
    )
    chat_id2, response_hash2 = example_streaming_without_hash(
        base_url, auth_token, stream_request_str
    )
    chat_id3, response_hash3 = example_non_streaming_with_hash(
        base_url, auth_token, non_stream_request_str, non_stream_calculated_hash
    )
    chat_id4, response_hash4 = example_non_streaming_without_hash(
        base_url, auth_token, non_stream_request_str
    )

    # Verify signatures for all requests
    print("\n=== Signature Verification for All Requests ===")
    verify_signature_for_chat(
        base_url,
        auth_token,
        chat_id1,
        stream_calculated_hash,
        response_hash1,
        "Streaming with X-Request-Hash",
    )
    verify_signature_for_chat(
        base_url,
        auth_token,
        chat_id2,
        None,
        response_hash2,
        "Streaming without X-Request-Hash",
    )
    verify_signature_for_chat(
        base_url,
        auth_token,
        chat_id3,
        non_stream_calculated_hash,
        response_hash3,
        "Non-streaming with X-Request-Hash",
    )
    verify_signature_for_chat(
        base_url,
        auth_token,
        chat_id4,
        None,
        response_hash4,
        "Non-streaming without X-Request-Hash",
    )


if __name__ == "__main__":
    main()

import requests
import json
import base64
import web3
import eth_account

URL_PREFIX = "https://inference-api.phala.network"


def get_attestation_report():
    """
    Get the attestation report from tdx service
    """
    url = f"{URL_PREFIX}/v1/attestation/report"
    response = requests.get(url)
    print("response", response.content)
    return response.json()


def verify_attestation_report(quote: dict):
    """
    Verify the attestation report with via NVIDIA and Intel attestation services
    """
    # GPU attestation verification
    url = "https://nras.attestation.nvidia.com/v3/attest/gpu"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    payload = json.loads(quote["nvidia_payload"])
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    print("GPU attestation verification result: ", result)

    # Intel attestation verification
    # For Automata example, just need to convert the returned base64 encoded quote
    # to hex format (take Node for example).
    intel_quote_bytes = "0x" + base64.b64decode(quote["intel_quote"]).hex()
    print("Intel quote bytes: ", intel_quote_bytes)
    print(
        """
    // Use on-chain smart contract function `verifyAndAttestOnChain` https://explorer.ata.network/address/0xE26E11B257856B0bEBc4C759aaBDdea72B64351F/contract/65536_2/readContract#F6
    // to verify with the printed quote bytes above.
    """
    )

    return result


def send_vllm_chat_completions():
    """
    Send chat completion request to vllm service
    """
    url = f"{URL_PREFIX}/v1/chat/completions"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    request_body = {
        "messages": [
            {"content": "You are a helpful assistant.", "role": "system"},
            {"content": "What is your model name?", "role": "user"},
        ],
        "stream": True,
        "model": "meta-llama/meta-llama-3.1-8b-instruct",
    }
    response = requests.post(url, headers=headers, json=request_body)
    chat_id = None
    for line in response.content.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8").replace("data: ", ""))
            if "id" in data:
                chat_id = data["id"]
                break
    response_body = response.content.decode("utf-8")
    return chat_id, request_body, response_body


def get_signature(chat_id: str):
    """
    Get the signature from vllm service
    """
    url = f"{URL_PREFIX}/v1/signature/{chat_id}"
    response = requests.get(url)
    data = response.json()
    return data["text"], data["signature"]


def verify_signature(signing_address: str, signature: str, text: str):
    """
    Verify the signature with via web3.eth.verifyMessage
    """
    w3 = web3.Web3()
    message = eth_account.messages.encode_defunct(text=text)
    try:
        verified = (
            w3.eth.account.recover_message(message, signature=signature)
            == signing_address
        )
        return verified
    except Exception as e:
        print(f"Failed to verify signature: {e}")
        return False


if __name__ == "__main__":
    # 1. Get quote from tdx
    quote = get_attestation_report()
    signing_address = quote["signing_address"]
    print("Quote: ", quote)

    # 2. Verify attestation report
    verify_attestation_report(quote)

    # 3. Sent chat request to vllm service
    chat_id = send_vllm_chat_completions()

    # 4. Get signature from vllm service
    text, signature = get_signature(chat_id)

    # 5. Verify signature
    verify_signature(signing_address, signature, text)

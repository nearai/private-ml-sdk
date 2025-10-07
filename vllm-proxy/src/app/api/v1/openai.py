import json
import os
from hashlib import sha256
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Header, Query
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
    Response,
)

from app.api.helper.auth import verify_authorization_header
from app.api.response.response import (
    invalid_signing_algo,
    not_found,
    unexpect_error,
)
from app.cache.cache import cache
from app.logger import log
from app.quote.quote import (
    ECDSA,
    ED25519,
    ecdsa_context,
    ed25519_context,
    generate_attestation,
    sign_message,
)

router = APIRouter(tags=["openai"])

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://vllm:8000")
VLLM_URL = f"{VLLM_BASE_URL}/v1/chat/completions"
VLLM_COMPLETIONS_URL = f"{VLLM_BASE_URL}/v1/completions"
VLLM_METRICS_URL = f"{VLLM_BASE_URL}/metrics"
VLLM_MODELS_URL = f"{VLLM_BASE_URL}/v1/models"
TIMEOUT = 60 * 10

COMMON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def sign_request(request: dict, response: str):
    content = json.dumps(request.get("messages", [])) + "\n" + response
    return quote.sign(content)


def hash(payload: str):
    return sha256(payload.encode()).hexdigest()


def sign_chat(text: str):
    return dict(
        text=text,
        signature_ecdsa=sign_message(ecdsa_context, text),
        signing_address_ecdsa=ecdsa_context.signing_address,
        signature_ed25519=sign_message(ed25519_context, text),
        signing_address_ed25519=ed25519_context.signing_address,
    )


async def stream_vllm_response(
    url: str,
    request_body: bytes,
    modified_request_body: bytes,
    request_hash: Optional[str] = None,
):
    """
    Handle streaming vllm request
    Args:
        request_body: The original request body
        modified_request_body: The modified enhanced request body
        request_hash: Optional hash from request header (X-Request-Hash). Used by trusted clients to provide
                     pre-calculated request hash, avoiding redundant hash computation. Falls back to
                     calculating hash from request_body if not provided
    Returns:
        A streaming response
    """
    if request_hash:
        request_sha256 = request_hash
        log.info(f"Using client-provided request hash: {request_sha256}")
    else:
        request_sha256 = sha256(request_body).hexdigest()
        log.debug(f"Calculated request hash: {request_sha256}")

    chat_id = None
    h = sha256()

    async def generate_stream(response):
        nonlocal chat_id, h
        async for chunk in response.aiter_text():
            h.update(chunk.encode())
            # Extract the cache key (data.id) from the first chunk
            if not chat_id:
                data = chunk.strip("data: ").strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    chunk_data = json.loads(data)
                    chat_id = chunk_data.get("id")
                except Exception as e:
                    error_message = f"Failed to parse the first chunk: {e}\n The original data is: {data}"
                    log.error(error_message)
                    raise Exception(error_message)

            yield chunk

        response_sha256 = h.hexdigest()
        # Cache the full request and response using the extracted cache key
        if chat_id:
            cache.set_chat(
                chat_id, json.dumps(sign_chat(f"{request_sha256}:{response_sha256}"))
            )
        else:
            error_message = "Chat id could not be extracted from the response"
            log.error(error_message)
            raise Exception(error_message)

    client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT), headers=COMMON_HEADERS)
    # Forward the request to the vllm backend
    req = client.build_request("POST", url, content=modified_request_body)
    response = await client.send(req, stream=True)
    # If not 200, return the error response directly without streaming
    if response.status_code != 200:
        error_content = await response.aread()
        await response.aclose()
        await client.aclose()

        return Response(
            content=error_content,
            status_code=response.status_code,
            headers=response.headers,
        )

    return StreamingResponse(
        generate_stream(response),
        background=BackgroundTasks([response.aclose, client.aclose]),
        media_type="text/event-stream",
    )


# Function to handle non-streaming responses
async def non_stream_vllm_response(
    url: str,
    request_body: bytes,
    modified_request_body: bytes,
    request_hash: Optional[str] = None,
):
    """
    Handle non-streaming responses
    Args:
        request_body: The original request body
        modified_request_body: The modified enhanced request body
        request_hash: Optional hash from request header (X-Request-Hash). Used by trusted clients to provide
                     pre-calculated request hash, avoiding redundant hash computation. Falls back to
                     calculating hash from request_body if not provided
    Returns:
        The response data
    """
    if request_hash:
        request_sha256 = request_hash
        log.info(f"Using client-provided request hash: {request_sha256}")
    else:
        request_sha256 = sha256(request_body).hexdigest()
        log.debug(f"Calculated request hash: {request_sha256}")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(TIMEOUT), headers=COMMON_HEADERS
    ) as client:
        response = await client.post(url, content=modified_request_body)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        response_data = response.json()
        # Cache the request-response pair using the chat ID
        chat_id = response_data.get("id")
        if chat_id:
            response_sha256 = sha256(response.content).hexdigest()
            cache.set_chat(
                chat_id, json.dumps(sign_chat(f"{request_sha256}:{response_sha256}"))
            )
        else:
            raise Exception("Chat id could not be extracted from the response")

        return response_data


def strip_empty_tool_calls(payload: dict) -> dict:
    """
    Strip empty tool calls from the payload
    To fix the bug of:
    https://github.com/vllm-project/vllm/pull/14054
    """
    if "messages" not in payload:
        return payload

    filtered_messages = []
    for message in payload["messages"]:
        # If the message has tool_calls, filter out empty ones
        if (
            "tool_calls" in message
            and isinstance(message["tool_calls"], list)
            and len(message["tool_calls"]) == 0
        ):
            del message["tool_calls"]
        filtered_messages.append(message)

    payload["messages"] = filtered_messages
    return payload


# Get attestation report of intel quote and nvidia payload
@router.get("/attestation/report", dependencies=[Depends(verify_authorization_header)])
async def attestation_report(
    request: Request,
    signing_algo: str | None = None,
    nonce: str | None = Query(None),
):
    signing_algo = ECDSA if signing_algo is None else signing_algo
    if signing_algo not in [ECDSA, ED25519]:
        return invalid_signing_algo()

    context = ecdsa_context if signing_algo == ECDSA else ed25519_context
    try:
        attestation = generate_attestation(context, nonce)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = cache.get_attestation(context.signing_address) or {}
    existing[signing_algo] = attestation
    cache.set_attestation(context.signing_address, existing)

    resp = dict(attestation)
    try:
        attestations = cache.get_attestations() or []
        collected = []
        for item in attestations:
            if isinstance(item, dict) and signing_algo in item:
                collected.append(item[signing_algo])
        resp["all_attestations"] = collected
        return resp
    except Exception as e:
        log.error(f"Error parsing the attestations in cache: {e}")
        return unexpect_error("Error parsing the attestations in cache", e)


# VLLM Chat completions
@router.post("/chat/completions", dependencies=[Depends(verify_authorization_header)])
async def chat_completions(
    request: Request,
    x_request_hash: Optional[str] = Header(None, alias="X-Request-Hash"),
):
    # Keep original request body to calculate the request hash for attestation
    request_body = await request.body()
    request_json = json.loads(request_body)
    modified_json = strip_empty_tool_calls(request_json)

    # Check if the request is for streaming or non-streaming
    is_stream = modified_json.get(
        "stream", False
    )  # Default to non-streaming if not specified

    modified_request_body = json.dumps(modified_json).encode("utf-8")
    if is_stream:
        # Create a streaming response
        return await stream_vllm_response(
            VLLM_URL, request_body, modified_request_body, x_request_hash
        )
    else:
        # Handle non-streaming response
        response_data = await non_stream_vllm_response(
            VLLM_URL, request_body, modified_request_body, x_request_hash
        )
        return JSONResponse(content=response_data)


# VLLM completions
@router.post("/completions", dependencies=[Depends(verify_authorization_header)])
async def completions(
    request: Request,
    x_request_hash: Optional[str] = Header(None, alias="X-Request-Hash"),
):
    # Keep original request body to calculate the request hash for attestation
    request_body = await request.body()
    request_json = json.loads(request_body)
    modified_json = strip_empty_tool_calls(request_json)

    # Check if the request is for streaming or non-streaming
    is_stream = modified_json.get(
        "stream", False
    )  # Default to non-streaming if not specified

    modified_request_body = json.dumps(modified_json).encode("utf-8")
    if is_stream:
        # Create a streaming response
        return await stream_vllm_response(
            VLLM_COMPLETIONS_URL, request_body, modified_request_body, x_request_hash
        )
    else:
        # Handle non-streaming response
        response_data = await non_stream_vllm_response(
            VLLM_COMPLETIONS_URL, request_body, modified_request_body, x_request_hash
        )
        return JSONResponse(content=response_data)


# Get signature for chat_id of chat history
@router.get("/signature/{chat_id}", dependencies=[Depends(verify_authorization_header)])
async def signature(request: Request, chat_id: str, signing_algo: str = None):
    cache_value = cache.get_chat(chat_id)
    if cache_value is None:
        return not_found("Chat id not found or expired")

    signature = None
    signing_algo = ECDSA if signing_algo is None else signing_algo

    # Retrieve the cached request and response
    try:
        value = json.loads(cache_value)
    except Exception as e:
        log.error(f"Failed to parse the cache value: {cache_value} {e}")
        return unexpect_error("Failed to parse the cache value", e)

    signing_address = None
    if signing_algo == ECDSA:
        signature = value.get("signature_ecdsa")
        signing_address = value.get("signing_address_ecdsa")
    elif signing_algo == ED25519:
        signature = value.get("signature_ed25519")
        signing_address = value.get("signing_address_ed25519")
    else:
        return invalid_signing_algo()

    return dict(
        text=value.get("text"),
        signature=signature,
        signing_address=signing_address,
        signing_algo=signing_algo,
    )


# Metrics of vLLM instance
@router.get("/metrics")
async def metrics(request: Request):
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
        response = await client.get(VLLM_METRICS_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return PlainTextResponse(response.text)


@router.get("/models")
async def models(request: Request):
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
        response = await client.get(VLLM_MODELS_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json())

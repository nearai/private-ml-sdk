import json
import httpx
import os

from fastapi import APIRouter, Request, Header, HTTPException, Depends, BackgroundTasks
from hashlib import sha256
from fastapi.responses import StreamingResponse, JSONResponse
from cachetools import TTLCache

from app.quote.quote import quote, ED25519, ECDSA
from app.api.response.response import ok, error
from app.logger import log
from app.api.helper.auth import verify_authorization_header

router = APIRouter(tags=["openai"])

VLLM_URL = "http://vllm:8000/v1/chat/completions"
TIMEOUT = 60 * 5

# Cache for storing full request-response pairs (TTL of 5 minutes)
cache = TTLCache(maxsize=1000, ttl=300)


def sign_request(request: dict, response: str):
    content = json.dumps(request.get("messages", [])) + "\n" + response
    return quote.sign(content)


def hash(payload: str):
    return sha256(payload.encode()).hexdigest()


async def stream_vllm_response(request_body: bytes):
    request_sha256 = sha256(request_body).hexdigest()

    # Modify the request body to use the correct model path and lowercasemodel name
    request_json = json.loads(request_body)
    request_json["model"] = "/mnt/models/" + request_json["model"].lower()
    modified_request_body = json.dumps(request_json)

    chat_id = None
    h = sha256()
    
    async def generate_stream(response):
        nonlocal chat_id, h
        async for chunk in response.aiter_text():
            h.update(chunk.encode())
            # Extract the cache key (data.id) from the first chunk
            if not chat_id:
                try:
                    data = chunk.strip("data: ").strip()
                    chunk_data = json.loads(data)
                    chat_id = chunk_data.get("id")
                except Exception as e:
                    raise Exception(f"Failed to parse the first chunk: {e}")
            yield chunk
        
        response_sha256 = h.hexdigest()
        # Cache the full request and response using the extracted cache key
        if chat_id:
            cache[chat_id] = f"{request_sha256}:{response_sha256}"
        else:
            raise Exception("Chat id could not be extracted from the response")

    client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT))
    # Forward the request to the vllm backend
    req = client.build_request("POST", VLLM_URL, content=modified_request_body)
    response = await client.send(req, stream=True)
    # If not 200, return the error response directly without streaming
    if response.status_code != 200:
        error_content = await response.aread()
        await response.aclose()
        await client.aclose()
        return JSONResponse(
            status_code=response.status_code,
            content=json.loads(error_content)
        )

    return StreamingResponse(
        generate_stream(response),
        background=BackgroundTasks([response.aclose, client.aclose])
    )

# Function to handle non-streaming responses
async def non_stream_vllm_response(request_body: bytes):
    request_sha256 = sha256(request_body).hexdigest()

    # Modify the request body to use the correct model path and lowercase model name
    request_json = json.loads(request_body)
    request_json["model"] = "/mnt/models/" + request_json["model"].lower()
    modified_request_body = json.dumps(request_json)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(TIMEOUT)
    ) as client:  # Increase timeout to 60 seconds
        # Forward the request to the vllm backend
        response = await client.post(VLLM_URL, content=modified_request_body)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )
        return response.json()


# Get attestation report of intel quote and nvidia payload
@router.get("/attestation/report", dependencies=[Depends(verify_authorization_header)])
async def attestation_report(request: Request):
    return dict(
        signing_address=quote.signing_address,
        intel_quote=quote.intel_quote,
        nvidia_payload=quote.nvidia_payload,
    )


# VLLM Chat completions
@router.post("/chat/completions", dependencies=[Depends(verify_authorization_header)])
async def chat_completions(request: Request):
    # Get the JSON body from the incoming request
    request_body = await request.body()
    request_json = json.loads(request_body)

    # Check if the request is for streaming or non-streaming
    is_stream = request_json.get(
        "stream", True
    )  # Default to streaming if not specified

    if is_stream:
        # Create a streaming response
        return await stream_vllm_response(request_body)
    else:
        # Handle non-streaming response
        response_data = await non_stream_vllm_response(request_body)
        return JSONResponse(content=response_data)


# Get signature for chat_id of chat history
@router.get("/signature/{chat_id}", dependencies=[Depends(verify_authorization_header)])
async def signature(request: Request, chat_id: str, signing_algo: str = None):
    if chat_id not in cache:
        return error("Chat id not found or expired", "chat_id_not_found")

    if signing_algo is None:
        signing_algo = quote.signing_method
    elif signing_algo not in [ED25519, ECDSA]:
        return error("Invalid signing algorithm. Must be 'ed25519' or 'ecdsa'", "invalid_signing_algo")

    # Retrieve the cached request and response
    chat_data = cache[chat_id]
    signature = quote.sign(chat_data)
    return dict(
        text=chat_data,
        signature=signature,
        signing_algo=signing_algo,
    )

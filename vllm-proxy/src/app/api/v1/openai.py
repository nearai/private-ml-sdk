import json
import httpx

from fastapi import APIRouter, Request, Header, HTTPException, Depends
from hashlib import sha256
from fastapi.responses import StreamingResponse
from cachetools import TTLCache

from app.quote.quote import quote
from app.api.response.response import ok, error
from app.logger import log

router = APIRouter(tags=["openai"])

VLLM_URL = "http://vllm:8000/v1/chat/completions"

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
    async with httpx.AsyncClient() as client:
        # Forward the request to the vllm backend
        async with client.stream("POST", VLLM_URL, content=modified_request_body) as response:
            # Check if the response status is OK
            if response.status_code != 200:
                raise Exception(
                    f"Backend error: {response.status_code}, {await response.text()}"
                )

            # Stream the response content back to the client
            async for chunk in response.aiter_text():
                h.update(chunk.encode())
                # Extract the cache key (data.id) from the first chunk
                if not chat_id:
                    try:
                        # Parse the first chunk as JSON to extract data.id
                        chunk_data = json.loads(chunk.strip("data: ").strip())
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


# Get attestation report of intel quote and nvidia payload
@router.get("/attestation/report")
async def attestation_report(request: Request):
    return dict(
        signing_address=quote.signing_address,
        intel_quote=quote.intel_quote,
        nvidia_payload=quote.nvidia_payload,
    )


# VLLM Chat completions
@router.post("/chat/completions")
async def chat_completions(request: Request):
    # Get the JSON body from the incoming request
    request_body = await request.body()

    # Create a streaming response
    return StreamingResponse(
        stream_vllm_response(request_body), media_type="text/event-stream"
    )


# Get signature for chat_id of chat history
@router.get("/signature/{chat_id}")
async def signature(request: Request, chat_id: str):
    if chat_id not in cache:
        return error("Chat id not found or expired", "chat_id_not_found")

    # Retrieve the cached request and response
    chat_data = cache[chat_id]
    signature = quote.sign(chat_data)
    return dict(
        text=chat_data,
        signature=signature,
    )

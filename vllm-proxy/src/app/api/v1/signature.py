from fastapi import APIRouter, Request
from quote.quote import quote
from hashlib import sha256

router = APIRouter(tags=["signature"])


@router.get("/v1/signature")
async def signature(request: Request):
    body = await request.json()
    return ok(sign_request(body))


def sign_request(request: str):
    h = sha256(request.encode())
    return dict(
        intel_quote=quote.intel_quote,
        nvidia_payload=quote.nvidia_payload,
        signing_address=quote.signing_address,
        request_sha256=h.digest().hex(),
    )

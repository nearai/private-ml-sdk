import json
import os
import hashlib
from dataclasses import dataclass
from typing import Optional, Callable

import eth_utils
import pynvml
import web3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dstack_sdk import DstackClient
from eth_account.messages import encode_defunct
from nv_attestation_sdk import attestation
from verifier import cc_admin
from app.logger import log

ED25519 = "ed25519"
ECDSA = "ecdsa"
GPU_ARCH = "HOPPER"
NO_GPU_MODE = os.getenv("GPU_NO_HW_MODE", "0").lower() in {"1", "true", "yes"}


@dataclass
class SigningContext:
    method: str
    signing_address: str
    signing_address_bytes: bytes
    _ed_private: Optional[Ed25519PrivateKey] = None
    _raw_account: Optional[web3.Account] = None

    def sign(self, content: str) -> str:
        if self.method == ED25519 and self._ed_private:
            signature = self._ed_private.sign(content.encode("utf-8"))
            return signature.hex()
        if self.method == ECDSA and self._raw_account:
            signed_message = self._raw_account.sign_message(encode_defunct(text=content))
            return f"0x{signed_message.signature.hex()}"
        raise ValueError("Signing context is not properly initialised")


def _build_report_data(signing_address_bytes: bytes, nonce: bytes) -> bytes:
    """Build TDX report data: [signing_address (padded to 32 bytes) || nonce (32 bytes)]"""
    if not signing_address_bytes:
        raise ValueError("Signing address must be provided")
    if len(signing_address_bytes) > 32:
        raise ValueError("Signing address exceeds 32 bytes")
    if len(nonce) != 32:
        raise ValueError("Nonce must be 32 bytes")
    return signing_address_bytes.ljust(32, b"\x00") + nonce


def _parse_nonce(nonce: Optional[bytes | str]) -> bytes:
    if nonce is None:
        return os.urandom(32)
    if isinstance(nonce, bytes):
        nonce_bytes = nonce
    else:
        try:
            nonce_bytes = bytes.fromhex(nonce)
        except ValueError as exc:
            raise ValueError("Nonce must be hex-encoded") from exc
    if len(nonce_bytes) != 32:
        raise ValueError("Nonce must be 32 bytes")
    return nonce_bytes


def _collect_gpu_evidence(nonce_hex: str, no_gpu_mode: bool) -> list:
    if no_gpu_mode:
        log.info("GPU evidence no-GPU mode enabled; using canned evidence")
        return cc_admin.collect_gpu_evidence_remote(nonce_hex, no_gpu_mode=True)

    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 1:
            return cc_admin.collect_gpu_evidence_remote(nonce_hex)
        attester = attestation.Attestation()
        attester.set_name("HOPPER")
        attester.set_nonce(nonce_hex)
        attester.set_claims_version("2.0")
        attester.set_ocsp_nonce_disabled(True)
        attester.add_verifier(
            dev=attestation.Devices.GPU,
            env=attestation.Environment["REMOTE"],
            url=None,
            evidence="",
        )
        return attester.get_evidence(options={"ppcie_mode": False})
    except pynvml.NVMLError as error:
        log.error("NVML error while collecting GPU evidence: %s", error)
        raise Exception("NVML error during GPU evidence collection") from error
    except Exception as error:
        log.error("GPU evidence collection failed: %s", error)
        raise
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass


def _build_nvidia_payload(nonce_hex: str, evidences: list) -> str:
    data = {"nonce": nonce_hex, "evidence_list": evidences, "arch": GPU_ARCH}
    return json.dumps(data)


def _create_ed25519_context() -> SigningContext:
    private_key = Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signing_address = public_key_bytes.hex()
    return SigningContext(
        method=ED25519,
        signing_address=signing_address,
        signing_address_bytes=public_key_bytes,
        _ed_private=private_key,
    )


def _create_ecdsa_context() -> SigningContext:
    w3 = web3.Web3()
    account = w3.eth.account.create()
    signing_address = account.address
    # Use the 20-byte Ethereum address for attestation (standard verification identifier)
    address_bytes = bytes.fromhex(signing_address[2:])  # Remove '0x' prefix
    return SigningContext(
        method=ECDSA,
        signing_address=signing_address,
        signing_address_bytes=address_bytes,
        _raw_account=account,
    )


ecdsa_context = _create_ecdsa_context()
ed25519_context = _create_ed25519_context()


def sign_message(context: SigningContext, content: str) -> str:
    return context.sign(content)


def generate_attestation(
    context: SigningContext, nonce: Optional[bytes | str] = None
) -> dict:
    request_nonce_bytes = _parse_nonce(nonce)
    request_nonce_hex = request_nonce_bytes.hex()

    # Build TDX report data: signing_address || request_nonce
    report_data = _build_report_data(context.signing_address_bytes, request_nonce_bytes)

    client = DstackClient()
    quote_result = client.get_quote(report_data)
    event_log = json.loads(quote_result.event_log)

    # Use request_nonce directly for GPU attestation
    gpu_evidence = _collect_gpu_evidence(request_nonce_hex, NO_GPU_MODE)
    if not gpu_evidence:
        raise Exception("No GPU evidence found")
    nvidia_payload = _build_nvidia_payload(request_nonce_hex, gpu_evidence)

    info = client.info().model_dump()

    return dict(
        signing_address=context.signing_address,
        signing_algo=context.method,
        request_nonce=request_nonce_hex,
        intel_quote=quote_result.quote,
        nvidia_payload=nvidia_payload,
        event_log=event_log,
        info=info,
    )


__all__ = [
    "SigningContext",
    "sign_message",
    "generate_attestation",
    "ecdsa_context",
    "ed25519_context",
    "ED25519",
    "ECDSA",
]

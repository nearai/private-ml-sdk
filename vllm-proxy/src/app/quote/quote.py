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
    attested_key_bytes: bytes
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


def _build_report_data(identifier: bytes, nonce: bytes) -> bytes:
    if not identifier:
        raise ValueError("Identifier must be provided")
    if len(identifier) > 32:
        raise ValueError("Identifier exceeds 32 bytes")
    if len(nonce) != 32:
        raise ValueError("Nonce must be 32 bytes")
    return identifier.ljust(32, b"\x00") + nonce


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


def _augment_info(info: dict) -> dict:
    tcb_info = info.get("tcb_info") if isinstance(info.get("tcb_info"), dict) else None
    compose = tcb_info.get("app_compose") if tcb_info else None
    if compose:
        calc_hash = hashlib.sha256(compose.encode("utf-8")).hexdigest()
        info["calculated_compose_hash"] = calc_hash
        info["compose_hash_match"] = calc_hash == info.get("compose_hash")
    if tcb_info and "mr_config" in tcb_info:
        info["mr_config"] = tcb_info["mr_config"]
    return info


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
        attested_key_bytes=public_key_bytes,
        _ed_private=private_key,
    )


def _create_ecdsa_context() -> SigningContext:
    w3 = web3.Web3()
    account = w3.eth.account.create()
    signing_address = account.address
    pub_key_bytes = account._key_obj.public_key.to_bytes()
    attested_key_bytes = eth_utils.keccak(pub_key_bytes)
    return SigningContext(
        method=ECDSA,
        signing_address=signing_address,
        attested_key_bytes=attested_key_bytes,
        _raw_account=account,
    )


ecdsa_context = _create_ecdsa_context()
ed25519_context = _create_ed25519_context()


def sign_message(context: SigningContext, content: str) -> str:
    return context.sign(content)


def generate_attestation(
    context: SigningContext, nonce: Optional[bytes | str] = None
) -> dict:
    nonce_bytes = _parse_nonce(nonce)
    nonce_hex = nonce_bytes.hex()
    report_data = _build_report_data(context.attested_key_bytes, nonce_bytes)

    client = DstackClient()
    quote_result = client.get_quote(report_data)
    event_log = json.loads(quote_result.event_log)

    gpu_evidence = _collect_gpu_evidence(nonce_hex, NO_GPU_MODE)
    if not gpu_evidence:
        raise Exception("No GPU evidence found")
    nvidia_payload = _build_nvidia_payload(nonce_hex, gpu_evidence)

    info = client.info().model_dump()
    info = _augment_info(info)

    return dict(
        signing_address=context.signing_address,
        signing_key=context.attested_key_bytes.hex(),
        nonce=nonce_hex,
        report_data=report_data.hex(),
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

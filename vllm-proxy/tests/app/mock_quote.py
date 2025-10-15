"""Mock quote module used in unit tests."""
import json
import os
from dataclasses import dataclass

ED25519 = "ed25519"
ECDSA = "ecdsa"
GPU_ARCH = "HOPPER"


@dataclass
class SigningContext:
    method: str
    signing_address: str
    attested_key_bytes: bytes

    def sign(self, content: str) -> str:
        if self.method == ECDSA:
            return f"0xmocked_{content}"
        return f"mocked_{content}"


ed25519_context = SigningContext(ED25519, "11" * 32, b"\x01" * 32)
ecdsa_context = SigningContext(ECDSA, "0xMockECDSAAddress", b"\x02" * 32)


def sign_message(context: SigningContext, content: str) -> str:
    return context.sign(content)


def _report_data(identifier: bytes, nonce: bytes) -> bytes:
    return identifier.ljust(32, b"\x00") + nonce


def generate_attestation(context: SigningContext, nonce=None) -> dict:
    if nonce is None:
        nonce_hex = "aa" * 32
    elif isinstance(nonce, bytes):
        nonce_hex = nonce.hex()
    else:
        nonce_hex = nonce

    nonce_bytes = bytes.fromhex(nonce_hex)
    report_data = _report_data(context.attested_key_bytes, nonce_bytes)

    payload = json.dumps({"nonce": nonce_hex, "evidence_list": [{"mock": "evidence"}], "arch": GPU_ARCH})
    info = {
        "compose_hash": "deadbeef",
        "calculated_compose_hash": "deadbeef",
        "compose_hash_match": True,
        "mr_config": "01deadbeef",
        "tcb_info": {"app_compose": "services: []", "mr_config": "01deadbeef"},
    }

    return dict(
        signing_address=context.signing_address,
        signing_key=context.attested_key_bytes.hex(),
        nonce=nonce_hex,
        report_data=report_data.hex(),
        intel_quote="mock_intel_quote",
        nvidia_payload=payload,
        event_log={"mock": True},
        info=info,
    )


def build_payload(nonce, evidences, cert_chain=None):  # compatibility helper
    return json.dumps({"nonce": nonce, "evidence_list": evidences, "arch": GPU_ARCH})


ecdsa_quote = ecdsa_context
ed25519_quote = ed25519_context

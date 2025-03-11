import web3
import eth_utils
import base64
import hashlib
import json
import eth_account
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from dstack_sdk import TappdClient
from verifier import cc_admin
from eth_account.messages import encode_defunct


ED25519 = "ed25519"
ECDSA = "ecdsa"
SIGNING_METHOD = os.getenv("SIGNING_METHOD", ED25519)


class Quote:

    def __init__(self, signing_method: str):
        self.signing_method = signing_method
        self.signing_address = None
        self.intel_quote = None
        self.nvidia_payload = None

        self.raw_acct = None
        self.ed25519_key = None

    def init(self, force=False):
        """
        Initialize the quote object.
        If the signing address is already set, it will not be re-initialized.
        If force is True, the signing address will be forced to be re-initialized.
        """
        if self.signing_address is not None and not force:
            return

        if self.signing_method == ED25519:
            self.init_ed25519()
        elif self.signing_method == ECDSA:
            self.init_ecdsa()
        else:
            raise ValueError("Unsupported signing method")

        gpu_evidence = cc_admin.collect_gpu_evidence(self.public_key)[0]
        gpu_report = gpu_evidence.get_attestation_report().hex()
        gpu_cert_chain = gpu_evidence.CertificateChains.extract_gpu_cert_chain_base64(
            gpu_evidence.CertificateChains.GpuAttestationCertificateChain
        )

        self.intel_quote = self.get_quote(self.public_key)
        self.nvidia_payload = self.build_payload(
            self.signing_address,
            gpu_report,
            gpu_cert_chain,
        )

        return dict(
            intel_quote=self.intel_quote,
            nvidia_payload=self.nvidia_payload,
            signing_address=self.signing_address,
        )

    def init_ed25519(self):
        # Generate Ed25519 key pair
        self.ed25519_key = Ed25519PrivateKey.generate()
        self.public_key_bytes = self.ed25519_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = self.public_key_bytes.hex()
        self.signing_address = self.public_key

    def init_ecdsa(self):
        # Generate web3 (ECDSA) account
        w3 = web3.Web3()
        self.raw_acct = w3.eth.account.create()
        self.signing_address = self.raw_acct.address
        self.public_key = eth_utils.keccak(
            self.raw_acct._key_obj.public_key.to_bytes()
        ).hex()

    def get_quote(self, public_key: str):
        # Initialize the client
        client = TappdClient()

        # Get quote for a message
        result = client.tdx_quote(public_key)
        quote = bytes.fromhex(result.quote)
        self.intel_quote = base64.b64encode(quote).decode("utf-8")
        return result.quote

    def sign(self, content: str):
        if self.signing_method == ED25519:
            return self._sign_ed25519(content)
        elif self.signing_method == ECDSA:
            return self._sign_ecdsa(content)
        else:
            raise ValueError("Unsupported signing method")

    def _sign_ed25519(self, content: str):
        # Sign content using ed25519
        message_bytes = content.encode("utf-8")
        signature = self.ed25519_key.sign(message_bytes)
        return signature.hex()

    def _sign_ecdsa(self, content: str):
        # Sign content using web3 (ECDSA)
        signed_message = self.raw_acct.sign_message(encode_defunct(text=content))
        return f"0x{signed_message.signature.hex()}"

    def build_payload(self, nonce, evidence, cert_chain):
        data = dict()
        data["nonce"] = nonce
        data["arch"] = "HOPPER"

        # Encode the evidence in Base64
        encoded_evidence_bytes = evidence.encode("ascii")
        encoded_evidence = base64.b64encode(encoded_evidence_bytes).decode("utf-8")
        data["evidence_list"] = [
            {"evidence": encoded_evidence, "certificate": str(cert_chain)}
        ]
        payload = json.dumps(data)
        return payload


ecdsa_quote = Quote(signing_method=ECDSA)
ecdsa_quote.init()

ed25519_quote = Quote(signing_method=ED25519)
ed25519_quote.init()


if __name__ == "__main__":
    quote = Quote(signing_method=ED25519)
    quote.init()
    print(
        dict(
            signing_address=quote.signing_address,
            intel_quote=quote.intel_quote,
            nvidia_payload=quote.nvidia_payload,
        )
    )

    quote2 = Quote(signing_method=ECDSA)
    quote2.init()
    print(
        dict(
            signing_address=quote2.signing_address,
            intel_quote=quote2.intel_quote,
            nvidia_payload=quote2.nvidia_payload,
        )
    )

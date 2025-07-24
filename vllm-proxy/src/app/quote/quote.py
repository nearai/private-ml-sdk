import json
import os

import eth_utils
import pynvml
import web3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dstack_sdk import TappdClient
from eth_account.messages import encode_defunct
from nv_attestation_sdk import attestation
from verifier import cc_admin

ED25519 = "ed25519"
ECDSA = "ecdsa"
GPU_ARCH = "HOPPER"
SIGNING_METHOD = os.getenv("SIGNING_METHOD", ED25519)


class Quote:

    def __init__(self, signing_method: str):
        self.signing_method = signing_method
        self.signing_address = None
        self.intel_quote = None
        self.nvidia_payload = None
        self.event_log = None
        self.info = None

        self.raw_acct = None
        self.ed25519_key = None

    def init(self, force=False) -> dict:
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

        self.intel_quote, self.event_log = self.get_quote(self.public_key)
        self.nvidia_payload = self.get_gpu_payload(self.public_key)
        self.info = self.get_info()

        return dict(
            signing_address=self.signing_address,
            intel_quote=self.intel_quote,
            nvidia_payload=self.nvidia_payload,
            event_log=self.event_log,
            info=self.info,
        )

    def get_gpu_payload(self, public_key: str) -> str:
        gpu_evidence_list = []
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count == 1:
                gpu_evidence_list = cc_admin.collect_gpu_evidence_remote(public_key)
            else:
                switch_attestation_mode = "REMOTE"
                switch_attester = attestation.Attestation()
                switch_attester.set_name("HOPPER")
                switch_attester.set_nonce(public_key)
                switch_attester.set_claims_version("2.0")
                switch_attester.set_ocsp_nonce_disabled(True)
                switch_attester.add_verifier(
                    dev=attestation.Devices.GPU,
                    env=attestation.Environment[switch_attestation_mode],
                    url=None,
                    evidence="",
                )
                gpu_evidence_list = switch_attester.get_evidence(
                    options={"ppcie_mode": False}
                )
        except pynvml.NVMLError as error:
            raise Exception(f"CUDA Error: {error}")
        finally:
            pynvml.nvmlShutdown()

        if len(gpu_evidence_list) == 0:
            raise Exception("No GPU evidence found")

        return self.build_payload(public_key, gpu_evidence_list)

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
        event_log = json.loads(result.event_log)
        return result.quote, event_log

    def get_info(self):
        import http.client
        import socket

        data = json.dumps({"report_data": self.public_key})
        headers = {"Content-Type": "application/json"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect("/var/run/tappd.sock")

            conn = http.client.HTTPConnection("localhost")
            conn.sock = sock

            try:
                conn.request(
                    "POST", "/prpc/Tappd.Info?json", body=data, headers=headers
                )
                response = conn.getresponse().read().decode()
                return json.loads(response)
            finally:
                conn.close()

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

    def build_payload(self, nonce, evidences):
        """
        A function that builds a payload with the given nonce and list of evidences.
        """
        data = {"nonce": nonce, "evidence_list": evidences, "arch": GPU_ARCH}
        return json.dumps(data)


ecdsa_quote = Quote(signing_method=ECDSA)
ecdsa_quote.init()

ed25519_quote = Quote(signing_method=ED25519)
ed25519_quote.init()


if __name__ == "__main__":
    print("ECDSA quote:")
    print(
        dict(
            signing_address=ecdsa_quote.signing_address,
            intel_quote=ecdsa_quote.intel_quote,
            nvidia_payload=ecdsa_quote.nvidia_payload,
        )
    )

    print("ED25519 quote:")
    print(
        dict(
            signing_address=ed25519_quote.signing_address,
            intel_quote=ed25519_quote.intel_quote,
            nvidia_payload=ed25519_quote.nvidia_payload,
        )
    )

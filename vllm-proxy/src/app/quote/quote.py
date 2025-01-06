import web3
import eth_utils
import base64, json
import subprocess
import eth_account
import json
import socket

from http.client import HTTPConnection
from dstack_sdk import TappdClient
from verifier import cc_admin


class Quote:
    def __init__(self):
        self.signing_address = None
        self.intel_quote = None
        self.nvidia_payload = None
        self.raw_acct = None

    def init(self):
        if self.raw_acct is None:
            w3 = web3.Web3()
            self.raw_acct = w3.eth.account.create()
            self.signing_address = self.raw_acct.address
            pub_keccak = eth_utils.keccak(
                self.raw_acct._key_obj.public_key.to_bytes()
            ).hex()
            gpu_evidence = cc_admin.collect_gpu_evidence(pub_keccak)[0]

            self.intel_quote = self.get_quote(pub_keccak)
            self.nvidia_payload = self.build_payload(
                pub_keccak,
                gpu_evidence["attestationReportHexStr"],
                gpu_evidence["certChainBase64Encoded"],
            )

        return dict(
            intel_quote=self.intel_quote,
            nvidia_payload=self.nvidia_payload,
            signing_address=self.signing_address,
        )

    def get_quote(self, pub_keccak: str):
        # Initialize the client
        client = TappdClient()

        # Get quote for a message
        result = client.tdx_quote(pub_keccak)
        quote = bytes.fromhex(result.quote)
        self.intel_quote = base64.b64encode(quote).decode("utf-8")
        return result.quote

    def sign(self, content: str):
        return self.raw_acct.sign_message(
            eth_account.messages.encode_defunct(text=content)
        ).signature.hex()

    def build_payload(self, nonce, evidence, cert_chain):
        data = dict()
        data["nonce"] = nonce
        data["arch"] = "HOPPER"
        encoded_evidence_bytes = evidence.encode("ascii")
        encoded_evidence = base64.b64encode(encoded_evidence_bytes)
        encoded_evidence = encoded_evidence.decode("utf-8")
        data["evidence_list"] = [
            {"evidence": encoded_evidence, "certificate": str(cert_chain)}
        ]
        payload = json.dumps(data)
        return payload


quote = Quote()
quote.init()

if __name__ == "__main__":
    print(
        dict(
            signing_address=quote.signing_address,
            intel_quote=quote.intel_quote,
            nvidia_payload=quote.nvidia_payload,
        )
    )

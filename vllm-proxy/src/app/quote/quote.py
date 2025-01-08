import base64
import json
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
from dstack_sdk import TappdClient
from verifier import cc_admin


class Quote:
    def __init__(self):
        self.signing_key = None
        self.verifying_key = None
        self.intel_quote = None
        self.nvidia_payload = None

    def init(self):
        if self.signing_key is None:
            # Generate a new Ed25519 key pair
            self.signing_key = SigningKey.generate()
            self.verifying_key = self.signing_key.verify_key

            # Convert the public key to a hexadecimal string
            pub_hex = self.verifying_key.encode(encoder=HexEncoder).decode("utf-8")

            # Collect GPU evidence using the public key
            gpu_evidence = cc_admin.collect_gpu_evidence(pub_hex)[0]

            # Generate the Intel quote and NVIDIA payload
            self.intel_quote = self.get_quote(pub_hex)
            self.nvidia_payload = self.build_payload(
                pub_hex,
                gpu_evidence["attestationReportHexStr"],
                gpu_evidence["certChainBase64Encoded"],
            )

        return dict(
            intel_quote=self.intel_quote,
            nvidia_payload=self.nvidia_payload,
            verifying_key=self.verifying_key.encode(encoder=HexEncoder).decode("utf-8"),
        )

    def get_quote(self, pub_hex: str):
        # Initialize the client
        client = TappdClient()

        # Get quote for a message
        result = client.tdx_quote(pub_hex)
        quote = bytes.fromhex(result.quote)
        self.intel_quote = base64.b64encode(quote).decode("utf-8")
        return result.quote

    def sign(self, content: str):
        # Sign the content using the Ed25519 signing key
        signed_message = self.signing_key.sign(content.encode("utf-8"))
        return base64.b64encode(signed_message.signature).decode("utf-8")

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

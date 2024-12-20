import web3
import eth_utils
import base64, json
import subprocess
import eth_account
import http.client, json, socket

from verifier import cc_admin
from app.logger import log


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

            # quote = subprocess.check_output(["tdx_quote"], input=pub_keccak.encode())
            quote = self.get_quote(pub_keccak)
            self.intel_quote = base64.b64encode(quote).decode("utf-8")
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
        try:
            data = json.dumps({"report_data": pub_keccak})
            headers = {"Content-Type": "application/json"}

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect("/var/run/tappd.sock")

            with http.client.HTTPConnection("localhost") as conn:
                conn.sock = sock
                conn.request(
                    "POST", "/prpc/Tappd.TdxQuote?json", body=data, headers=headers
                )
                return conn.getresponse().read().decode()
        except Exception as e:
            log.error(f"Failed to get quote: {e}")
            return None

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

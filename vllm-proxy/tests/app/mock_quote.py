"""Mock quote module for testing"""
import json
import os
from unittest.mock import MagicMock

# Mock the imports that would fail in test environment
eth_utils = MagicMock()
pynvml = MagicMock()
web3 = MagicMock()
Ed25519PrivateKey = MagicMock()
TappdClient = MagicMock()
encode_defunct = MagicMock()
attestation = MagicMock()
cc_admin = MagicMock()

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
        
        # Mock data
        self.public_key = "mock_public_key_" + signing_method
        self.public_key_bytes = b"mock_public_key_bytes"
    
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
            
        # Mock implementations
        self.intel_quote = "mock_intel_quote_" + self.signing_method
        self.event_log = {"test": "event_log", "method": self.signing_method}
        self.nvidia_payload = json.dumps({
            "nonce": self.public_key,
            "evidence_list": [{"mock": "evidence"}],
            "arch": GPU_ARCH
        })
        self.info = {"test": "info", "method": self.signing_method}
        
        return dict(
            signing_address=self.signing_address,
            intel_quote=self.intel_quote,
            nvidia_payload=self.nvidia_payload,
            event_log=self.event_log,
            info=self.info,
        )
    
    def get_gpu_payload(self, public_key: str) -> str:
        # Mock GPU payload
        gpu_evidence_list = [{"mock": "gpu_evidence"}]
        return self.build_payload(public_key, gpu_evidence_list)
    
    def init_ed25519(self):
        # Mock Ed25519 initialization
        self.ed25519_key = MagicMock()
        self.public_key = "mock_ed25519_public_key"
        self.signing_address = self.public_key
        
    def init_ecdsa(self):
        # Mock ECDSA initialization
        self.raw_acct = MagicMock()
        self.raw_acct.address = "0xMockECDSAAddress"
        self.raw_acct._key_obj = MagicMock()
        self.raw_acct._key_obj.public_key = MagicMock()
        self.raw_acct._key_obj.public_key.to_bytes = MagicMock(return_value=b"mock_ecdsa_pubkey_bytes")
        self.signing_address = self.raw_acct.address
        self.public_key = "mock_ecdsa_public_key"
    
    def get_quote(self, public_key: str):
        # Mock quote retrieval
        return "mock_quote_" + public_key, {"test": "event_log"}
    
    def get_info(self):
        # Mock info retrieval
        return {"test": "info", "report_data": self.public_key}
    
    def sign(self, content: str):
        if self.signing_method == ED25519:
            return self._sign_ed25519(content)
        elif self.signing_method == ECDSA:
            return self._sign_ecdsa(content)
        else:
            raise ValueError("Unsupported signing method")
    
    def _sign_ed25519(self, content: str):
        # Mock Ed25519 signing
        return f"ed25519_signature_{content}"
    
    def _sign_ecdsa(self, content: str):
        # Mock ECDSA signing
        return f"0xecdsa_signature_{content}"
    
    def build_payload(self, nonce, evidence, cert_chain=None):
        """
        A function that builds a payload with the given nonce and evidence.
        This mock supports both the 2-arg (nonce, evidences) and 3-arg (nonce, evidence, cert_chain) signatures.
        """
        import base64
        
        # Handle different call signatures
        if isinstance(evidence, str) and cert_chain is not None:
            # 3-arg signature from test
            evidence_list = [{
                "evidence": base64.b64encode(evidence.encode("ascii")).decode("utf-8"),
                "certificate": cert_chain
            }]
        elif isinstance(evidence, list):
            # 2-arg signature with evidence list
            evidence_list = evidence
        else:
            # 2-arg signature with single evidence
            evidence_list = [evidence]
            
        data = {"nonce": nonce, "evidence_list": evidence_list, "arch": GPU_ARCH}
        return json.dumps(data)


# Create mock instances with initialized data
ecdsa_quote = Quote(signing_method=ECDSA)
ecdsa_quote.init()

ed25519_quote = Quote(signing_method=ED25519)
ed25519_quote.init()

import unittest
import base64
import json
from unittest.mock import patch, MagicMock, patch

patch.TEST_PREFIX = ("test", "setUp")

# Init mocked values
# 1. Verifier
mock_verifier = MagicMock()
mock_verifier.cc_admin = MagicMock()
mock_verifier.cc_admin.collect_gpu_evidence.return_value = [
    {
        "attestationReportHexStr": "mock_attestation_report",
        "certChainBase64Encoded": "mock_cert_chain",
    }
]
# 2. Dstack SDK
mock_dstack_sdk = MagicMock()
mock_client = mock_dstack_sdk.TappdClient.return_value
mock_result = MagicMock()
mock_result.quote = "614756736247383d"  # 'hello'
mock_client.tdx_quote.return_value = mock_result


@patch.dict("sys.modules", {"verifier": mock_verifier, "dstack_sdk": mock_dstack_sdk})
class TestQuote(unittest.TestCase):

    def test_init_ed25519(self):
        # Test initialization with ed25519 signing
        from app.quote.quote import Quote

        quote = Quote(signing_method="ed25519")
        result = quote.init()

        self.assertIsNotNone(result["signing_address"])
        self.assertIsNotNone(result["intel_quote"])
        self.assertIsNotNone(result["nvidia_payload"])
        self.assertEqual(quote.signing_method, "ed25519")

    def test_init_ecdsa(self):
        # Test initialization with web3 (ECDSA) signing
        from app.quote.quote import Quote

        quote = Quote(signing_method="ecdsa")
        result = quote.init(force=True)

        self.assertIsNotNone(result["signing_address"])
        self.assertIsNotNone(result["intel_quote"])
        self.assertIsNotNone(result["nvidia_payload"])
        self.assertEqual(quote.signing_method, "ecdsa")

    def test_sign_ed25519(self):
        # Test signing using ed25519
        from app.quote.quote import Quote

        quote = Quote(signing_method="ed25519")
        quote.init()
        content = "Test message"
        signature = quote.sign(content)

        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)

    def test_sign_ecdsa(self):
        # Test signing using web3 (ECDSA)
        from app.quote.quote import Quote

        quote = Quote(signing_method="ecdsa")
        quote.init()
        content = "Test message"
        signature = quote.sign(content)

        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)

    def test_build_payload(self):
        # Test payload building
        from app.quote.quote import Quote

        quote = Quote(signing_method="ed25519")
        quote.init()
        nonce = "mock_nonce"
        evidence = "mock_evidence"
        cert_chain = "mock_cert_chain"

        payload = quote.build_payload(nonce, evidence, cert_chain)
        self.assertIsInstance(payload, str)

        # Verify payload structure
        payload_data = json.loads(payload)
        self.assertEqual(payload_data["nonce"], nonce)
        self.assertEqual(payload_data["arch"], "HOPPER")
        self.assertEqual(
            payload_data["evidence_list"][0]["evidence"],
            base64.b64encode(evidence.encode("ascii")).decode("utf-8"),
        )
        self.assertEqual(payload_data["evidence_list"][0]["certificate"], cert_chain)


if __name__ == "__main__":
    unittest.main()

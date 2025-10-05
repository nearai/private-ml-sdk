import unittest
import base64
import json
from unittest.mock import MagicMock, patch

from tests.app.sample_dstack_data import SAMPLE_DSTACK_INFO, SAMPLE_DSTACK_QUOTE

patch.TEST_PREFIX = ("test", "setUp")

ED25519 = "ed25519"
ECDSA = "ecdsa"

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
mock_client = mock_dstack_sdk.DstackClient.return_value

mock_quote_response = MagicMock()
mock_quote_response.quote = SAMPLE_DSTACK_QUOTE["quote"]
mock_quote_response.event_log = SAMPLE_DSTACK_QUOTE["event_log"]
mock_quote_response.model_dump.return_value = SAMPLE_DSTACK_QUOTE
mock_client.get_quote.return_value = mock_quote_response

mock_info_response = MagicMock()
mock_info_response.model_dump.return_value = SAMPLE_DSTACK_INFO
mock_client.info.return_value = mock_info_response

# 3. pynvml
mock_pynvml = MagicMock()
mock_pynvml.nvmlInit.return_value = None
mock_pynvml.nvmlDeviceGetCount.return_value = 1
mock_pynvml.nvmlShutdown.return_value = None

# 4. nv_attestation_sdk
mock_attestation_sdk = MagicMock()
mock_attestation = mock_attestation_sdk.attestation.Attestation.return_value
mock_attestation.get_evidence.return_value = [{"mock": "evidence"}]


@patch.dict(
    "sys.modules",
    {
        "verifier": mock_verifier,
        "dstack_sdk": mock_dstack_sdk,
        "pynvml": mock_pynvml,
        "nv_attestation_sdk": mock_attestation_sdk,
    },
)
class TestQuote(unittest.TestCase):

    def setUp(self):
        mock_client.get_quote.reset_mock()
        mock_attestation.get_evidence.reset_mock()

    def test_init_ed25519(self):
        # Test initialization with ed25519 signing
        from app.quote.quote import Quote

        quote = Quote(signing_method=ED25519)
        result = quote.init()

        self.assertIsNotNone(result["signing_address"])
        self.assertIsNotNone(result["intel_quote"])
        self.assertIsNotNone(result["nvidia_payload"])
        self.assertEqual(quote.signing_method, ED25519)

    def test_init_ecdsa(self):
        # Test initialization with web3 (ECDSA) signing
        from app.quote.quote import Quote

        quote = Quote(signing_method=ECDSA)
        result = quote.init(force=True)

        self.assertIsNotNone(result["signing_address"])
        self.assertIsNotNone(result["intel_quote"])
        self.assertIsNotNone(result["nvidia_payload"])
        self.assertEqual(quote.signing_method, ECDSA)

    def test_sign_ed25519(self):
        # Test signing using ed25519
        from app.quote.quote import Quote

        quote = Quote(signing_method=ED25519)
        quote.init()
        content = "Test message"
        signature = quote.sign(content)

        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)

    def test_sign_ecdsa(self):
        # Test signing using web3 (ECDSA)
        from app.quote.quote import Quote

        quote = Quote(signing_method=ECDSA)
        quote.init()
        content = "Test message"
        signature = quote.sign(content)

        self.assertIsInstance(signature, str)
        self.assertGreater(len(signature), 0)

    def test_build_payload(self):
        # Test payload building
        from app.quote.quote import Quote

        quote = Quote(signing_method=ED25519)
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

    def test_init_unsupported_signing_method(self):
        # Test unsupported signing method
        from app.quote.quote import Quote

        with self.assertRaises(ValueError):
            quote = Quote("unsupported_method")
            quote.init()

    def test_sign_unsupported_signing_method(self):
        # Test unsupported signing method for signing
        from app.quote.quote import Quote

        quote = Quote("unsupported_method")
        with self.assertRaises(ValueError):
            quote.sign("test_message")

    def test_report_data_accepts_20_byte_wallet(self):
        from app.quote.quote import Quote

        address = "0x" + "ab" * 20
        data = Quote._report_data(address)
        expected = bytes.fromhex(address[2:]).ljust(64, b"\x00")
        self.assertEqual(data, expected)

    def test_report_data_accepts_32_byte_wallet(self):
        from app.quote.quote import Quote

        address = "cd" * 32
        data = Quote._report_data(address)
        expected = bytes.fromhex(address).ljust(64, b"\x00")
        self.assertEqual(data, expected)

    def test_report_data_rejects_invalid_length(self):
        from app.quote.quote import Quote

        with self.assertRaises(ValueError):
            Quote._report_data("0x" + "12" * 21)

    def test_report_data_rejects_non_hex(self):
        from app.quote.quote import Quote

        with self.assertRaises(ValueError):
            Quote._report_data("0xZZ" + "12" * 19)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from nacl.signing import VerifyKey, SigningKey
import base64
import json

from app.quote.quote import Quote


class TestQuote(unittest.TestCase):
    def setUp(self):
        """Set up a Quote instance and mock dependencies."""
        self.quote = Quote()

    @patch("cc_admin.collect_gpu_evidence")
    @patch("TappdClient")
    def test_init(self, mock_tappd_client, mock_collect_gpu_evidence):
        """Test the initialization of the Quote class."""
        # Mock GPU evidence and TappdClient response
        mock_collect_gpu_evidence.return_value = [
            {
                "attestationReportHexStr": "mock_attestation_report",
                "certChainBase64Encoded": "mock_cert_chain",
            }
        ]
        mock_tappd_client_instance = MagicMock()
        mock_tappd_client_instance.tdx_quote.return_value = MagicMock(
            quote="mock_quote_hex"
        )
        mock_tappd_client.return_value = mock_tappd_client_instance

        # Initialize the Quote object
        result = self.quote.init()

        # Assertions
        self.assertIn("intel_quote", result)
        self.assertIn("nvidia_payload", result)
        self.assertIn("verifying_key", result)

        # Ensure the signing key and verifying key are generated
        self.assertIsNotNone(self.quote.signing_key)
        self.assertIsNotNone(self.quote.verifying_key)

        # Ensure the quote is Base64-encoded
        self.assertEqual(
            result["intel_quote"],
            base64.b64encode(bytes.fromhex("mock_quote_hex")).decode("utf-8"),
        )

        # Ensure the NVIDIA payload is correctly built
        payload = json.loads(result["nvidia_payload"])
        self.assertEqual(
            payload["nonce"], self.quote.verifying_key.encode().decode("utf-8")
        )
        self.assertEqual(payload["arch"], "HOPPER")

    @patch("your_module.TappdClient")
    def test_get_quote(self, mock_tappd_client):
        """Test the get_quote method."""
        # Mock TappdClient response
        mock_tappd_client_instance = MagicMock()
        mock_tappd_client_instance.tdx_quote.return_value = MagicMock(
            quote="mock_quote_hex"
        )
        mock_tappd_client.return_value = mock_tappd_client_instance

        # Call get_quote
        pub_hex = "mock_pub_hex"
        result = self.quote.get_quote(pub_hex)

        # Assertions
        self.assertEqual(result, "mock_quote_hex")
        self.assertEqual(
            self.quote.intel_quote,
            base64.b64encode(bytes.fromhex("mock_quote_hex")).decode("utf-8"),
        )

    def test_sign(self):
        """Test the sign method."""
        # Generate a signing key and set it in the Quote instance
        self.quote.signing_key = SigningKey.generate()

        # Sign a message
        message = "Test message"
        signature = self.quote.sign(message)

        # Verify the signature
        verify_key = VerifyKey(self.quote.signing_key.verify_key.encode())
        try:
            verify_key.verify(message.encode("utf-8"), base64.b64decode(signature))
        except Exception as e:
            self.fail(f"Signature verification failed: {e}")

    def test_build_payload(self):
        """Test the build_payload method."""
        nonce = "mock_nonce"
        evidence = "mock_evidence"
        cert_chain = "mock_cert_chain"

        # Build the payload
        payload = self.quote.build_payload(nonce, evidence, cert_chain)

        # Parse the payload
        payload_data = json.loads(payload)

        # Assertions
        self.assertEqual(payload_data["nonce"], nonce)
        self.assertEqual(payload_data["arch"], "HOPPER")
        self.assertEqual(
            payload_data["evidence_list"][0]["evidence"],
            base64.b64encode(evidence.encode("ascii")).decode("utf-8"),
        )
        self.assertEqual(payload_data["evidence_list"][0]["certificate"], cert_chain)

    @patch("your_module.cc_admin.collect_gpu_evidence")
    @patch("your_module.TappdClient")
    def test_full_workflow(self, mock_tappd_client, mock_collect_gpu_evidence):
        """Test the full workflow of the Quote class."""
        # Mock GPU evidence and TappdClient response
        mock_collect_gpu_evidence.return_value = [
            {
                "attestationReportHexStr": "mock_attestation_report",
                "certChainBase64Encoded": "mock_cert_chain",
            }
        ]
        mock_tappd_client_instance = MagicMock()
        mock_tappd_client_instance.tdx_quote.return_value = MagicMock(
            quote="mock_quote_hex"
        )
        mock_tappd_client.return_value = mock_tappd_client_instance

        # Initialize the Quote object
        result = self.quote.init()

        # Sign a message
        message = "Test message"
        signature = self.quote.sign(message)

        # Verify the signature
        verify_key = VerifyKey(self.quote.signing_key.verify_key.encode())
        try:
            verify_key.verify(message.encode("utf-8"), base64.b64decode(signature))
        except Exception as e:
            self.fail(f"Signature verification failed: {e}")

        # Assertions for init
        self.assertIn("intel_quote", result)
        self.assertIn("nvidia_payload", result)
        self.assertIn("verifying_key", result)

        # Assertions for payload
        payload = json.loads(result["nvidia_payload"])
        self.assertEqual(
            payload["nonce"], self.quote.verifying_key.encode().decode("utf-8")
        )
        self.assertEqual(payload["arch"], "HOPPER")


if __name__ == "__main__":
    unittest.main()

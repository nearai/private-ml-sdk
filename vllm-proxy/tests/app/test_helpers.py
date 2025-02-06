from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
from dataclasses import dataclass

# Mock TappdClient response
@dataclass
class MockTdxQuoteResult:
    quote: str = "deadbeef"  # Valid hex string for testing

def setup_verifier_mock():
    # Mock the verifier module
    mock_cc_admin = MagicMock()
    mock_cc_admin.collect_gpu_evidence.return_value = [{
        "attestationReportHexStr": "mock_report",
        "certChainBase64Encoded": "mock_cert_chain"
    }]
    mock_verifier = MagicMock()
    mock_verifier.cc_admin = mock_cc_admin
    sys.modules['verifier'] = mock_verifier

class MockTappdClientClass:
    def __init__(self):
        pass
    
    def tdx_quote(self, *args, **kwargs):
        return MockTdxQuoteResult()

def setup_dstack_mock():
    sys.modules['dstack_sdk'] = MagicMock()
    sys.modules['dstack_sdk'].TappdClient = MockTappdClientClass

def setup_test_environment():
    """
    This function must be called before importing any application code
    to ensure all necessary mocks are in place.
    """
    setup_verifier_mock()
    setup_dstack_mock()
    os.environ["TOKEN"] = 'test_token'
    os.environ["SIGNING_METHOD"] = 'ecdsa'

# Constants for testing
TEST_AUTH_HEADER = "Bearer test_token" 
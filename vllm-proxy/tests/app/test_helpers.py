from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
from dataclasses import dataclass

# Mock TappdClient response
@dataclass
class MockTdxQuoteResult:
    quote: str = "deadbeef"  # Valid hex string for testing
    event_log: str = '{"test": "event_log"}'  # Mock event log JSON string

def setup_verifier_mock():
    # Mock the verifier module
    mock_cc_admin = MagicMock()
    mock_cc_admin.collect_gpu_evidence.return_value = [{
        "attestationReportHexStr": "mock_report",
        "certChainBase64Encoded": "mock_cert_chain"
    }]
    mock_cc_admin.collect_gpu_evidence_remote.return_value = [{
        "attestationReportHexStr": "mock_report",
        "certChainBase64Encoded": "mock_cert_chain"
    }]
    mock_verifier = MagicMock()
    mock_verifier.cc_admin = mock_cc_admin
    sys.modules['verifier'] = mock_verifier
    sys.modules['verifier.cc_admin'] = mock_cc_admin

class MockTappdClientClass:
    def __init__(self):
        pass
    
    def tdx_quote(self, *args, **kwargs):
        return MockTdxQuoteResult()

def setup_dstack_mock():
    sys.modules['dstack_sdk'] = MagicMock()
    sys.modules['dstack_sdk'].TappdClient = MockTappdClientClass

def setup_pynvml_mock():
    # Mock pynvml module to avoid GPU dependency in tests
    mock_pynvml = MagicMock()
    mock_pynvml.nvmlInit = MagicMock()
    mock_pynvml.nvmlShutdown = MagicMock()
    mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
    mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock()
    mock_pynvml.nvmlDeviceGetName = MagicMock(return_value=b"Test GPU")
    mock_pynvml.nvmlDeviceGetSerial = MagicMock(return_value=b"TEST123")
    mock_pynvml.nvmlDeviceGetUUID = MagicMock(return_value=b"TEST-UUID-123")
    mock_pynvml.nvmlDeviceGetPciInfo = MagicMock(return_value=MagicMock(busId=b"0000:00:00.0"))
    mock_pynvml.NVML_SUCCESS = 0
    sys.modules['pynvml'] = mock_pynvml

def setup_attestation_mock():
    # Mock nv_attestation_sdk module
    mock_attestation = MagicMock()
    mock_attestation.Attestation = MagicMock
    mock_attestation.Devices = MagicMock()
    mock_attestation.Devices.GPU = "GPU"
    mock_attestation.Environment = {"REMOTE": "REMOTE"}
    sys.modules['nv_attestation_sdk'] = MagicMock()
    sys.modules['nv_attestation_sdk.attestation'] = mock_attestation

def setup_test_environment():
    """
    This function must be called before importing any application code
    to ensure all necessary mocks are in place.
    """
    setup_pynvml_mock()
    setup_verifier_mock()
    setup_dstack_mock()
    setup_attestation_mock()
    os.environ["TOKEN"] = 'test_token'
    os.environ["SIGNING_METHOD"] = 'ecdsa'

# Constants for testing
TEST_AUTH_HEADER = "Bearer test_token" 
import json
import sys
import types
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path


class TestQuote(unittest.TestCase):
    def setUp(self):
        self.mock_cc_admin = types.SimpleNamespace(
            collect_gpu_evidence_remote=lambda nonce: [{"mock": "gpu"}],
        )

        attestation_instance = types.SimpleNamespace(
            set_name=lambda *_: None,
            set_nonce=lambda *_: None,
            set_claims_version=lambda *_: None,
            set_ocsp_nonce_disabled=lambda *_: None,
            add_verifier=lambda **kwargs: None,
            get_evidence=lambda **kwargs: [{"mock": "gpu"}],
        )
        attestation_mod = types.SimpleNamespace(
            Attestation=lambda: attestation_instance,
            Devices=types.SimpleNamespace(GPU="GPU"),
            Environment={"REMOTE": "REMOTE"},
        )

        pynvml_mod = types.SimpleNamespace(
            nvmlInit=lambda: None,
            nvmlShutdown=lambda: None,
            nvmlDeviceGetCount=lambda: 1,
        )

        client = types.SimpleNamespace()
        client.get_quote = lambda report_data: types.SimpleNamespace(
            quote="mock_quote",
            event_log=json.dumps({"mock": True}),
        )
        client.info = lambda: types.SimpleNamespace(
            model_dump=lambda: {
                "compose_hash": "db669af634b75c7f298400f3b6c2aa8ba54998bac83e23d10ab4eaadc4b50ccf",
                "tcb_info": {"app_compose": "compose", "mr_config": "01db669af634b75c7f298400f3b6c2aa8ba54998bac83e23d10ab4eaadc4b50ccf"},
            }
        )
        dstack_mod = types.SimpleNamespace(DstackClient=lambda: client)

        self.original_modules = {}
        for name, module in {
            "verifier": types.SimpleNamespace(cc_admin=self.mock_cc_admin),
            "nv_attestation_sdk": types.SimpleNamespace(attestation=attestation_mod),
            "pynvml": pynvml_mod,
            "dstack_sdk": dstack_mod,
        }.items():
            if name in sys.modules:
                self.original_modules[name] = sys.modules[name]
            sys.modules[name] = module

        root = Path(__file__).resolve().parents[3] / "src"
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        if "app" not in sys.modules:
            sys.modules["app"] = types.ModuleType("app")
            sys.modules["app"].__path__ = [str(root / "app")]

        if "app.quote" not in sys.modules:
            quote_pkg = types.ModuleType("app.quote")
            quote_pkg.__path__ = [str(root / "app" / "quote")]
            sys.modules["app.quote"] = quote_pkg

        module_path = root / "app" / "quote" / "quote.py"
        loader = SourceFileLoader("app.quote.quote", str(module_path))
        spec = spec_from_loader(loader.name, loader)
        module = module_from_spec(spec)
        loader.exec_module(module)
        sys.modules["app.quote.quote"] = module

        self.quote = module

    def tearDown(self):
        sys.modules.update(self.original_modules)
        for key in ["verifier", "nv_attestation_sdk", "pynvml", "dstack_sdk", "app.quote.quote", "app.quote"]:
            sys.modules.pop(key, None)

    def test_generate_attestation_binds_nonce(self):
        nonce_hex = "aa" * 32
        result = self.quote.generate_attestation(self.quote.ed25519_context, nonce_hex)

        self.assertEqual(result["nonce"], nonce_hex)
        report_data_bytes = bytes.fromhex(result["report_data"])
        signing_key_bytes = bytes.fromhex(result["signing_key"])
        self.assertEqual(report_data_bytes[:32], signing_key_bytes.ljust(32, b"\x00"))
        self.assertEqual(report_data_bytes[32:], bytes.fromhex(nonce_hex))
        self.assertEqual(json.loads(result["nvidia_payload"])["nonce"], nonce_hex)
        self.assertTrue(result["info"]["compose_hash_match"])

    def test_build_report_data_layout(self):
        identifier = b"\x01" * 16
        nonce = b"\x02" * 32
        combined = self.quote._build_report_data(identifier, nonce)
        self.assertEqual(combined[:32], identifier.ljust(32, b"\x00"))
        self.assertEqual(combined[32:], nonce)

    def test_random_nonce_generation(self):
        result = self.quote.generate_attestation(self.quote.ed25519_context)
        self.assertEqual(len(bytes.fromhex(result["nonce"])), 32)
        self.assertEqual(len(bytes.fromhex(result["report_data"])), 64)



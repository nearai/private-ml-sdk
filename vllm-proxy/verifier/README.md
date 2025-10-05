# Confidential AI Verifier

Tools for validating Phala Cloud attestation and response signatures.

## Requirements

- Python 3.10+
- `requests`, `eth-account`, `web3`
- Phala Cloud API key (`API_KEY` env var for the signature verifier)

## Attestation verifier

Generates a fresh nonce, requests a new attestation, and checks:
- GPU quote via NVIDIA NRAS.
- TDX report data binds the runtime signing key and supplied nonce.
- Compose manifest hash matches the TDX measurement.

```bash
python3 attestation_verifier.py --api-key YOUR_API_KEY [--model MODEL_NAME]
```

## Signature verifier

Fetches chat completions, verifies the ECDSA signature, and cross-checks the
attested signing key and nonce against a fresh report.

```bash
export API_KEY=<YOUR_API_KEY>
python3 signature_verifier.py
```

Both scripts print links to the published Sigstore provenance so you can audit
the container image that generated the signatures.

# Confidential AI Verifier

Tools for validating Phala Cloud attestation and response signatures.

## Requirements

- Python 3.10+
- `requests`, `eth-account`, `web3`
- Phala Cloud API key from https://redpill.ai

## Setup

1. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   # Edit .env and set your API_KEY
   ```

2. Load environment variables:
   ```bash
   source .env
   ```

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
source .env  # Load API_KEY from .env file
python3 signature_verifier.py
```

Both scripts print links to the published Sigstore provenance so you can audit
the container image that generated the signatures.

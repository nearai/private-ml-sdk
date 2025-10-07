# Confidential AI Verifier

Tools for validating Phala Cloud attestation and response signatures.

## Requirements

- Python 3.10+
- `requests`, `eth-account`
- Phala Cloud API key from https://redpill.ai (for signature verifier only)

## Attestation Verifier

Generates a fresh nonce, requests a new attestation, and verifies:
- **GPU attestation**: Submits GPU evidence payload to NVIDIA NRAS (https://nras.attestation.nvidia.com) and verifies the nonce matches
- **TDX report data**: Validates that report data binds the signing key (ECDSA or Ed25519) and nonce
- **Intel TDX quote**: Verifies TDX quote via Phala's verification service (https://cloud-api.phala.network)
- **Compose manifest**: Displays Docker compose manifest and verifies it matches the mr_config measurement

### Usage

```bash
python3 attestation_verifier.py [--model MODEL_NAME]
```

Default model: `phala/deepseek-chat-v3-0324`

No API key required. The verifier fetches attestations from the public `/v1/attestation/report` endpoint.

### Example Output

```
Signing address: 0x1234...
Request nonce: abc123...

🔐 TDX report data
Signing algorithm: ecdsa
Report data binds signing address: True
Report data embeds request nonce: True

🔐 GPU attestation
GPU payload nonce matches request_nonce: True
NVIDIA attestation verdict: PASS

🔐 Intel TDX quote
Intel TDX quote verified: True
```

## Signature Verifier

Fetches chat completions (streaming and non-streaming), verifies ECDSA signatures, and validates attestations:
1. Sends chat completion request to `/v1/chat/completions`
2. Fetches signature from `/v1/signature/{chat_id}` endpoint
3. Verifies request hash and response hash match the signed hashes
4. Recovers ECDSA signing address from signature
5. Fetches fresh attestation for the recovered signing address
6. Validates attestation using the same checks as attestation verifier

### Setup

Set your API key as an environment variable:

```bash
export API_KEY=your-api-key-here
```

Or create a `.env` file:

```bash
API_KEY=your-api-key-here
```

Then load it:

```bash
source .env
python3 signature_verifier.py
```

### What It Verifies

- Request body hash matches server-computed hash
- Response text hash matches server-computed hash
- ECDSA signature is valid and recovers to the claimed signing address
- Signing address is bound to hardware via TDX report data
- GPU attestation passes NVIDIA verification
- Intel TDX quote is valid

## Sigstore Provenance

Both scripts automatically extract all container image digests from the Docker compose manifest (matching `@sha256:xxx` patterns) and verify Sigstore accessibility for each image. This allows you to:

1. Verify the container images were built from the expected source repository
2. Review the GitHub Actions workflow that built the images
3. Audit the build provenance and supply chain metadata

The verifiers check each Sigstore link with an HTTP HEAD request to ensure provenance data is available (not 404).

Example output:
```
🔐 Sigstore provenance
Checking Sigstore accessibility for container images...
  ✓ https://search.sigstore.dev/?hash=sha256:77fbe5f142419d6f52b04c0e749aa3facf9359dcd843f68d073e24d0eba7c5dd (HTTP 200)
  ✓ https://search.sigstore.dev/?hash=sha256:abc123... (HTTP 200)
```

If a link returns ✗, the provenance data may not be available in Sigstore (either the image wasn't signed or the digest is incorrect).

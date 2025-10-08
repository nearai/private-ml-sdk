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
cd verifiers
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
5. Fetches fresh attestation with user-supplied nonce for the recovered signing address
6. Validates attestation using the same checks as attestation verifier

**Note**: The verifier supplies a fresh nonce when fetching attestation (step 5), which ensures attestation freshness but means the nonce/report_data won't match the original signing context. This is expected behavior - the verifier proves the signing key is bound to valid hardware, not that a specific attestation was used for signing.

### Setup

Set your API key as an environment variable:

```bash
export API_KEY=your-api-key-here
```

Or create a `.env` file:

```bash
API_KEY=your-api-key-here
```

Then run from the verifiers directory:

```bash
cd verifiers
source .env
python3 signature_verifier.py [--model MODEL_NAME]
```

Default model: `phala/deepseek-chat-v3-0324`

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

## Multi-Server Load Balancer Setup

In production deployments with multiple backend servers behind a load balancer:

### Server Behavior
- Each server has its own unique signing key/address
- Attestation requests with `signing_address` parameter return 404 if the address doesn't match
- Response includes `all_attestations: [attestation]` (single-element array with this server's attestation)

### Load Balancer Requirements
When `/v1/attestation/report?signing_address={addr}&nonce={nonce}`:
1. **Broadcast** the request to all backend servers
2. Collect non-404 responses from servers matching the signing_address
3. Merge `all_attestations` arrays from all responses
4. Return combined response with all servers' attestations

### Verifier Flow
1. Get signature → extract `signing_address`
2. Request attestation with `signing_address` parameter
3. LB broadcasts → collect attestations from all servers
4. Verifier finds matching attestation by comparing `signing_address` in `all_attestations`

### Example Response (Multi-Server)
```json
{
  "signing_address": "0xServer1...",
  "intel_quote": "...",
  "all_attestations": [
    {"signing_address": "0xServer1...", "intel_quote": "...", ...},
    {"signing_address": "0xServer2...", "intel_quote": "...", ...}
  ]
}
```

The verifier filters `all_attestations` to find the entry matching the signature's `signing_address`.

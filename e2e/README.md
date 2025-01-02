# VLLM OpenAI with TDX Attestation

## VLLM Proxy

The VLLM Proxy wraps the VLLM service and provides a simple interface for obtaining the attestation report and verifying the signature of chat completions requests.

Following E2E example is designed to demonstrate how to use the VLLM Proxy and full steps of the attestation process.

Also, for the deployment, the vllm service can be deployed with `docker-compose.yml` in the `vllm-proxy/docker` directory, which refers to the [README.md](../vllm-proxy/README.md) for more details. Please note that the models are not included in the docker image, so you need to download the models and put them in the `--model` path.

The `vllm-proxy` and `vllm` services is deployed inside dstack CVM of TEE environment. Before launch the CVM, please make sure the `Local KMS` is running, which privide the essential keys for the CVM to be properly initialized. The Local KMS can be launched by following commands:

```bash
cd Private-ML-SDK/meta-dstack-nvidia/dstack/key-provider-build/
./run.sh
```

## E2E Example

The `e2e/e2e.py` script is designed to demonstrate the interaction with the VLLM service. Below is a detailed step-by-step guide on how to use this script effectively.

### Step-by-Step Guide

1. **Get Attestation Report**:
   - The script begins by fetching an attestation report from the TDX and GPU. This report includes crucial information such as the signing address and quotes from Intel and NVIDIA.

   The report including:
   - signing_address: The address that will be used to sign the response
   - intel_quote: The quote from Intel CPU
   - nvidia_payload: The quote from NVIDIA GPU

   ```python
   quote = get_attestation_report()
   signing_address = quote["signing_address"]
   intel_quote = quote["intel_quote"]
   nvidia_payload = quote["nvidia_payload"]
   ```


2. **Verify Attestation Report**:
   - The next step involves verifying the attestation report using NVIDIA and Intel attestation services. This ensures the integrity and authenticity of the report.

   ```python
   verify_attestation_report(quote)
   ```

    Verifying the attestation report includes:
    
    - NVIDIA verification: Sends a POST request to the NVIDIA attestation service with the NVIDIA payload from the quote. The response contains the result of the GPU attestation verification.
    - Intel verification: Theoretically, you can verify the Intel TDX quote with the value of intel_quote at anywhere that provide TDX quote verification service. The screenshot below is an example of how to verify the Intel TDX quote with the Automata's on-chain attestation smart contract.
   
   
3. **Send Chat Request**:
   
   Send a chat completion request with stream support to the VLLM service. 

   ```python
   chat_id, request_body, response_body = send_vllm_chat_completions()
   ```

    This request and its response will be cached for 5 minutes, and will be used to generate the signature for the response.

4. **Get Signature**:
   - The script then retrieves a signature from the VLLM service, which is used to verify the authenticity of the response.

   ```python
   text, signature = get_signature(chat_id)
   ```

   The response includes the text and the signature.
   - Text: the message you may want to verify. It is joined by the sha256 of the HTTP request body, and of the HTTP response body, separated by a colon :.
   - Signature: the signature of the text.

    Since the resource limitation, the signature will be kept in the memory for 5 minutes since the response is generated. 

5. **Verify Signature**:
   - Finally, verifies the signature using the signing address obtained earlier. This step ensures that the response has not been tampered with.

   ```python
   verify_signature(signing_address, signature, text)
   ```

   It is using web3.eth.verifyMessage to verify the signature.

   Also, the signature can be verified on Etherscan. Go to https://etherscan.io/verifiedSignatures, click Verify Signature:


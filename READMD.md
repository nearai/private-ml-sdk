# Private ML SDK

A secure and verifiable solution for running Large Language Models (LLMs) in Trusted Execution Environments (TEEs), leveraging NVIDIA GPU TEE and Intel TDX technologies.

![Architecture Overview](./assets/image/gpu-tee.webp)

## Overview

Private ML SDK provides a secure environment for running LLM workloads with guaranteed privacy and security, preventing unauthorized access to both the model and user data during inference operations. The solution leverages NVIDIA's TEE GPU technology (H100/H200/B100) and Intel CPUs with TDX support to ensure that AI model execution and data processing remain fully protected within secure enclaves.

Key features:
- Tamper-proof data processing
- Secure execution environment
- Open source and reproducible builds
- Verifiable execution results
- Nearly native speed performance (up to 99% efficiency)

## Architecture

The system consists of several core components:

- **Secure Compute Environment**: TEE-based execution environment
- **Remote Attestation**: Verification of the TEE environment
- **Secure Communication**: End-to-end encryption between users and LLM
- **Key Management Service (KMS)**: Key management service to manage keys for encryption and decryption

## Getting Started

TODO.

## Performance

Based on benchmarks running LLMs in NVIDIA H100 and H200:
- Efficiency approaches 99% as input size grows
- Minimal overhead for larger models (e.g., Phi3-14B-128k and Llama3.1-70B)
- Performance scales well with increased input sizes and model complexities
- I/O overhead becomes negligible in high-computation scenarios

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## References

- [NVIDIA Confidential Computing](https://www.nvidia.com/en-us/data-center/solutions/confidential-computing/)
- [Intel TDX Documentation](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-trust-domain-extensions.html)

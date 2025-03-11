#!/bin/bash

# Default version
VERSION=${1:-latest}

# Build the Docker image with the specified version
docker build \
    -f docker/Dockerfile \
    -t vllm-proxy:$VERSION \
    .

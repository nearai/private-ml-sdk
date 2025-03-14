#!/bin/bash

# Default image name
IMAGE=${1:-vllm-proxy:latest}

echo "Image: $IMAGE"

# Build the Docker image with the specified version
docker build \
    -f docker/Dockerfile \
    -t $IMAGE \
    .

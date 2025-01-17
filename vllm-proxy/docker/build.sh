#!/bin/bash

docker build \
    -f docker/Dockerfile \
    -t vllm-proxy:0.2.0 \
    .

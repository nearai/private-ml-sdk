#!/bin/bash

docker build \
    -f docker/Dockerfile \
    -t 0xii/vllm-proxy:0.2.5 \
    .

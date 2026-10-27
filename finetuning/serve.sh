#!/usr/bin/env bash
set -euo pipefail
export VLLM_USE_FLASHINFER_SAMPLER=0

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/../../vllm-venv/bin/activate"
cd "$SCRIPT_DIR"

vllm serve Qwen/Qwen2.5-0.5B-Instruct \
    --host 0.0.0.0 \
    --port 9000 \
    --served-model-name chat-small \
    --api-key dev-secret-abc \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.75 \
    --max-model-len 1024 \
    --enforce-eager \
    --enable-lora \
    --max-loras 3 \
    --max-lora-rank 16 \
    --lora-modules pirate=./adapters/pirate genz=./adapters/genz formal=./adapters/formal

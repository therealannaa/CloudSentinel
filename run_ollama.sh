#!/usr/bin/env bash
# Quick Ollama runner for CloudKC-Bench arms (free, local, no quota).
#
# Prereqs (one-time):
#   1. install Ollama         (macOS: brew install ollama  |  https://ollama.com)
#   2. start it:              ollama serve            (own terminal / background service)
#   3. pull a model:          ollama pull llama3.1    (or qwen2.5:7b, llama3.2:3b for small laptops)
#
# Usage:
#   ./run_ollama.sh                 # smoke test: 1 scenario, arm A2, 1 seed
#   ./run_ollama.sh full            # full ablation A1-A4 x dev x 3 seeds
# Env overrides: LLM_MODEL (default llama3.1), ENVIRONMENT (default localstack), DB_PATH.
set -euo pipefail
cd "$(dirname "$0")"

export LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:11434/v1}"
export LLM_API_KEY="${LLM_API_KEY:-ollama}"
export LLM_MODEL="${LLM_MODEL:-llama3.1}"
ENVIRONMENT="${ENVIRONMENT:-localstack}"
DB="${DB_PATH:-cloudsentinel.db}"

# Verify Ollama is reachable before spending time.
if ! curl -fsS "${LLM_BASE_URL%/v1}/api/tags" >/dev/null 2>&1; then
  echo "ERROR: Ollama not reachable at ${LLM_BASE_URL%/v1}."
  echo "  Start it with:   ollama serve"
  echo "  Pull the model:  ollama pull ${LLM_MODEL}"
  exit 1
fi
echo "Ollama reachable. Model=${LLM_MODEL}  env=${ENVIRONMENT}"

if [ "${1:-smoke}" = "full" ]; then
  python3 -m benchmark.cli --db "$DB" run-arms \
    --arms A1,A2,A3,A4 --set dev --seeds 3 --environment "$ENVIRONMENT" --csv results_ollama.csv
else
  echo "Smoke test (1 scenario, arm A2, 1 seed). Run './run_ollama.sh full' for the ablation."
  python3 -m benchmark.cli --db "$DB" run-arms \
    --arms A2 --set dev --limit 1 --seeds 1 --environment "$ENVIRONMENT"
fi

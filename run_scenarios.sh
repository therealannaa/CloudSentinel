#!/usr/bin/env bash
# CloudKC-Bench — generate a scenario set end-to-end (P2).
#   ./run_scenarios.sh dev        # 59 dev scenarios -> manifests + events
#   ./run_scenarios.sh all        # dev + held-out, then seal held-out
# Env: DB_PATH (default cloudsentinel.db), ENVIRONMENT (synthetic|localstack|real_aws)
set -euo pipefail
cd "$(dirname "$0")"

SET="${1:-dev}"
DB="${DB_PATH:-cloudsentinel.db}"
ENVIRONMENT="${ENVIRONMENT:-synthetic}"

python3 -m benchmark.cli --db "$DB" generate --set "$SET" --environment "$ENVIRONMENT"
python3 -m benchmark.cli --db "$DB" summary

if [ "$SET" = "all" ] || [ "$SET" = "heldout" ]; then
  python3 -m benchmark.cli --db "$DB" seal-heldout
fi

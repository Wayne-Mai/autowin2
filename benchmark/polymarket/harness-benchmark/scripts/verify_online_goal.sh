#!/usr/bin/env bash
set -euo pipefail

LAST_RUN_ENV="${LAST_RUN_ENV:-reports/polymarket_online_6h_last.env}"
USER_DB_PATH="${DB_PATH:-}"
USER_RUN_ID="${RUN_ID:-}"

if [[ -f "${LAST_RUN_ENV}" ]]; then
  source "${LAST_RUN_ENV}"
fi

DB_PATH="${USER_DB_PATH:-${DB_PATH:-data/polymarket_online_6h.sqlite}}"
RUN_ID="${USER_RUN_ID:-${RUN_ID:-polymarket-online-6h}}"

python3 -m polypaper.cli verify-online-goal \
  --db "${DB_PATH}" \
  --run-id "${RUN_ID}" \
  --target-roi 0.10 \
  --require-flat \
  --min-runtime-seconds 21600 \
  --min-strategies 2 \
  --min-strategy-families 2 \
  "$@"

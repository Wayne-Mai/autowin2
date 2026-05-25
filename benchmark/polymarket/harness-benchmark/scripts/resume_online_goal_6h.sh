#!/usr/bin/env bash
set -euo pipefail

LAST_RUN_ENV="${LAST_RUN_ENV:-reports/polymarket_online_6h_last.env}"

if [[ -f "${LAST_RUN_ENV}" ]]; then
  source "${LAST_RUN_ENV}"
elif [[ -z "${DB_PATH:-}" || -z "${RUN_ID:-}" ]]; then
  echo "missing ${LAST_RUN_ENV}; run scripts/online_goal_6h.sh first or set DB_PATH and RUN_ID" >&2
  exit 2
fi

REPORT_PATH="${REPORT_PATH:-reports/${RUN_ID}.md}"

DB_PATH="${DB_PATH}" RUN_ID="${RUN_ID}" REPORT_PATH="${REPORT_PATH}" \
  scripts/online_goal_6h.sh --resume "$@"

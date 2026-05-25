#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
DB_PATH="${DB_PATH:-data/polymarket_online_6h_${RUN_STAMP}.sqlite}"
RUN_ID="${RUN_ID:-polymarket-online-6h-${RUN_STAMP}}"
REPORT_PATH="${REPORT_PATH:-reports/polymarket_online_6h_${RUN_STAMP}.md}"
LAST_RUN_ENV="${LAST_RUN_ENV:-reports/polymarket_online_6h_last.env}"
MAX_CYCLES="${MAX_CYCLES:-4321}"
MIN_CYCLES_BEFORE_PASS="${MIN_CYCLES_BEFORE_PASS:-720}"
MIN_RUNTIME_SECONDS_BEFORE_PASS="${MIN_RUNTIME_SECONDS_BEFORE_PASS:-21600}"
DETECTION_DELAY_SECONDS="${DETECTION_DELAY_SECONDS:-1}"
POLLING_DELAY_SECONDS="${POLLING_DELAY_SECONDS:-5}"
DECISION_DELAY_SECONDS="${DECISION_DELAY_SECONDS:-1}"
EXECUTION_DELAY_SECONDS="${EXECUTION_DELAY_SECONDS:-2}"
SLIPPAGE_BPS="${SLIPPAGE_BPS:-0}"
FALLBACK_FEE_RATE="${FALLBACK_FEE_RATE:-0}"
FEE_EXPONENT="${FEE_EXPONENT:-1}"

mkdir -p "$(dirname "${LAST_RUN_ENV}")"
{
  printf 'DB_PATH=%q\n' "${DB_PATH}"
  printf 'RUN_ID=%q\n' "${RUN_ID}"
  printf 'REPORT_PATH=%q\n' "${REPORT_PATH}"
  printf 'MAX_CYCLES=%q\n' "${MAX_CYCLES}"
  printf 'MIN_CYCLES_BEFORE_PASS=%q\n' "${MIN_CYCLES_BEFORE_PASS}"
  printf 'MIN_RUNTIME_SECONDS_BEFORE_PASS=%q\n' "${MIN_RUNTIME_SECONDS_BEFORE_PASS}"
  printf 'DETECTION_DELAY_SECONDS=%q\n' "${DETECTION_DELAY_SECONDS}"
  printf 'POLLING_DELAY_SECONDS=%q\n' "${POLLING_DELAY_SECONDS}"
  printf 'DECISION_DELAY_SECONDS=%q\n' "${DECISION_DELAY_SECONDS}"
  printf 'EXECUTION_DELAY_SECONDS=%q\n' "${EXECUTION_DELAY_SECONDS}"
  printf 'SLIPPAGE_BPS=%q\n' "${SLIPPAGE_BPS}"
  printf 'FALLBACK_FEE_RATE=%q\n' "${FALLBACK_FEE_RATE}"
  printf 'FEE_EXPONENT=%q\n' "${FEE_EXPONENT}"
} > "${LAST_RUN_ENV}"

python3 -m polypaper.cli target-run-until \
  --db "${DB_PATH}" \
  --run-id "${RUN_ID}" \
  --max-cycles "${MAX_CYCLES}" \
  --min-cycles-before-pass "${MIN_CYCLES_BEFORE_PASS}" \
  --min-runtime-seconds-before-pass "${MIN_RUNTIME_SECONDS_BEFORE_PASS}" \
  --min-passing-strategies 2 \
  --min-passing-families 2 \
  --interval-seconds 5 \
  --market-limit 120 \
  --market-pages 3 \
  --max-assets 120 \
  --market-order liquidity \
  --market-prefer-keywords "up or down,updown" \
  --settlement-check-seconds 60 \
  --target-variants online_goal_grid \
  --maker-fill-mode queue_proxy \
  --maker-queue-ahead-fraction 1 \
  --maker-queue-decay 0.25 \
  --maker-max-order-age-attempts 24 \
  --maker-cancel-on-price-move \
  --maker-adverse-fill-on-price-move \
  --maker-adverse-fill-fraction 0.5 \
  --detection-delay-seconds "${DETECTION_DELAY_SECONDS}" \
  --polling-delay-seconds "${POLLING_DELAY_SECONDS}" \
  --decision-delay-seconds "${DECISION_DELAY_SECONDS}" \
  --execution-delay-seconds "${EXECUTION_DELAY_SECONDS}" \
  --slippage-bps "${SLIPPAGE_BPS}" \
  --fee-rate "${FALLBACK_FEE_RATE}" \
  --fee-exponent "${FEE_EXPONENT}" \
  --progress-every-cycles 60 \
  --require-flat \
  --out "${REPORT_PATH}" \
  "$@"

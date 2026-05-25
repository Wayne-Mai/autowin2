#!/usr/bin/env bash
set -euo pipefail

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
DB_PATH="${DB_PATH:-data/polymarket_online_6h_${RUN_STAMP}.sqlite}"
RUN_ID="${RUN_ID:-polymarket-online-6h-${RUN_STAMP}}"
REPORT_PATH="${REPORT_PATH:-reports/polymarket_online_6h_${RUN_STAMP}.md}"
LAST_RUN_ENV="${LAST_RUN_ENV:-reports/polymarket_online_6h_last.env}"
LOG_PATH="${LOG_PATH:-logs/polymarket_online_6h_${RUN_STAMP}.log}"
PID_PATH="${PID_PATH:-reports/polymarket_online_6h_last.pid}"
LABEL_PATH="${LABEL_PATH:-reports/polymarket_online_6h_last.label}"
PLIST_PATH="${PLIST_PATH:-reports/polymarket_online_6h_${RUN_STAMP}.plist}"
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
WORKDIR="$(pwd)"
if [[ "${LOG_PATH}" = /* ]]; then
  ABS_LOG_PATH="${LOG_PATH}"
else
  ABS_LOG_PATH="${WORKDIR}/${LOG_PATH}"
fi
if [[ "${PLIST_PATH}" = /* ]]; then
  ABS_PLIST_PATH="${PLIST_PATH}"
else
  ABS_PLIST_PATH="${WORKDIR}/${PLIST_PATH}"
fi

mkdir -p \
  "$(dirname "${LOG_PATH}")" \
  "$(dirname "${ABS_LOG_PATH}")" \
  "$(dirname "${PID_PATH}")" \
  "$(dirname "${LABEL_PATH}")" \
  "$(dirname "${PLIST_PATH}")" \
  "$(dirname "${ABS_PLIST_PATH}")" \
  "$(dirname "${LAST_RUN_ENV}")"

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

quote() {
  printf '%q' "$1"
}

xml_escape() {
  local value="$1"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  value="${value//\"/&quot;}"
  printf '%s' "${value}"
}

COMMAND="cd $(quote "${WORKDIR}") && "
COMMAND+="RUN_STAMP=$(quote "${RUN_STAMP}") "
COMMAND+="DB_PATH=$(quote "${DB_PATH}") "
COMMAND+="RUN_ID=$(quote "${RUN_ID}") "
COMMAND+="REPORT_PATH=$(quote "${REPORT_PATH}") "
COMMAND+="LAST_RUN_ENV=$(quote "${LAST_RUN_ENV}") "
COMMAND+="MAX_CYCLES=$(quote "${MAX_CYCLES}") "
COMMAND+="MIN_CYCLES_BEFORE_PASS=$(quote "${MIN_CYCLES_BEFORE_PASS}") "
COMMAND+="MIN_RUNTIME_SECONDS_BEFORE_PASS=$(quote "${MIN_RUNTIME_SECONDS_BEFORE_PASS}") "
COMMAND+="DETECTION_DELAY_SECONDS=$(quote "${DETECTION_DELAY_SECONDS}") "
COMMAND+="POLLING_DELAY_SECONDS=$(quote "${POLLING_DELAY_SECONDS}") "
COMMAND+="DECISION_DELAY_SECONDS=$(quote "${DECISION_DELAY_SECONDS}") "
COMMAND+="EXECUTION_DELAY_SECONDS=$(quote "${EXECUTION_DELAY_SECONDS}") "
COMMAND+="SLIPPAGE_BPS=$(quote "${SLIPPAGE_BPS}") "
COMMAND+="FALLBACK_FEE_RATE=$(quote "${FALLBACK_FEE_RATE}") "
COMMAND+="FEE_EXPONENT=$(quote "${FEE_EXPONENT}") "
COMMAND+="exec scripts/online_goal_6h.sh"
for arg in "$@"; do
  COMMAND+=" $(quote "${arg}")"
done

if command -v launchctl >/dev/null 2>&1; then
  SAFE_STAMP="$(printf '%s' "${RUN_STAMP}" | tr -c 'A-Za-z0-9._-' '-')"
  LABEL="${LABEL:-com.polypaper.online-goal.${SAFE_STAMP}}"
  cat > "${ABS_PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$(xml_escape "${LABEL}")</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>$(xml_escape "${COMMAND}")</string>
  </array>
  <key>StandardOutPath</key>
  <string>$(xml_escape "${ABS_LOG_PATH}")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "${ABS_LOG_PATH}.err")</string>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF
  launchctl bootstrap "gui/$(id -u)" "${ABS_PLIST_PATH}"
  printf '%s\n' "${LABEL}" > "${LABEL_PATH}"
  : > "${PID_PATH}"
  printf 'started label=%s log=%s stderr=%s label_file=%s plist=%s\n' "${LABEL}" "${ABS_LOG_PATH}" "${ABS_LOG_PATH}.err" "${LABEL_PATH}" "${ABS_PLIST_PATH}"
else
  nohup bash -c 'trap "" HUP TERM INT; eval "$1"' online_goal_6h "${COMMAND}" > "${LOG_PATH}" 2>&1 < /dev/null &
  PID=$!
  disown "${PID}" 2>/dev/null || true
  printf '%s\n' "${PID}" > "${PID_PATH}"
  : > "${LABEL_PATH}"
  printf 'started pid=%s log=%s pid_file=%s\n' "${PID}" "${LOG_PATH}" "${PID_PATH}"
fi

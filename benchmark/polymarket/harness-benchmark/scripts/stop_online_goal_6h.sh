#!/usr/bin/env bash
set -euo pipefail

PID_PATH="${PID_PATH:-reports/polymarket_online_6h_last.pid}"
LABEL_PATH="${LABEL_PATH:-reports/polymarket_online_6h_last.label}"
STOPPED=0

if [[ -f "${LABEL_PATH}" ]]; then
  LABEL="$(cat "${LABEL_PATH}")"
  if [[ -n "${LABEL}" ]] && command -v launchctl >/dev/null 2>&1; then
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    launchctl remove "${LABEL}" 2>/dev/null || true
    echo "stopped label=${LABEL}"
    STOPPED=1
  fi
fi

if [[ -f "${PID_PATH}" ]]; then
  PID="$(cat "${PID_PATH}")"
  if [[ -n "${PID}" ]]; then
    CHILDREN="$(pgrep -P "${PID}" 2>/dev/null || true)"
    TARGETS="${CHILDREN} ${PID}"

    kill ${TARGETS} 2>/dev/null || true
    sleep 2
    kill -9 ${TARGETS} 2>/dev/null || true

    echo "stopped pid=${PID}"
    STOPPED=1
  fi
fi

if [[ "${STOPPED}" -eq 0 ]]; then
  echo "missing active label or pid file" >&2
  exit 2
fi

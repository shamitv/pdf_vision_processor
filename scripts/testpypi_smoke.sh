#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TEST_PYPI_INDEX="https://test.pypi.org/simple"
PROD_PYPI_INDEX="https://pypi.org/simple"
PACKAGE_NAME="pdf-vision-processor"
SMOKE_PORT="${SMOKE_PORT:-9999}"
SMOKE_HOST="${SMOKE_HOST:-127.0.0.1}"

info() {
  printf "[smoke] %s\n" "$*"
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    info "Stopping CLI instance (pid=${SERVER_PID})"
    kill "${SERVER_PID}" 2>/dev/null || true
  fi
  if [[ -n "${SMOKE_DIR:-}" && -d "${SMOKE_DIR}" ]]; then
    rm -rf "${SMOKE_DIR}"
  fi
}

trap cleanup EXIT

info "Building distribution artifacts with version bump"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/build_dist.py" --bump patch

SMOKE_DIR="$(mktemp -d -t pdf-vision-smoke-XXXX)"
info "Created temporary smoke env at ${SMOKE_DIR}"

"${PYTHON_BIN}" -m venv "${SMOKE_DIR}/venv"
source "${SMOKE_DIR}/venv/bin/activate"
python -m pip install --upgrade pip >/dev/null

info "Installing ${PACKAGE_NAME} from TestPyPI"
pip install \
  --index-url "${TEST_PYPI_INDEX}" \
  --extra-index-url "${PROD_PYPI_INDEX}" \
  "${PACKAGE_NAME}" >/dev/null

info "Launching CLI for smoke check"
pdf-vision-processor --host "${SMOKE_HOST}" --port "${SMOKE_PORT}" --no-reload >/tmp/pdf_vision_smoke.log 2>&1 &
SERVER_PID=$!

info "Waiting for service to respond on ${SMOKE_HOST}:${SMOKE_PORT}"
for attempt in {1..30}; do
  if curl -fsS "http://${SMOKE_HOST}:${SMOKE_PORT}/" >/dev/null; then
    info "Smoke test passed"
    exit 0
  fi
  sleep 1
  info "Retry ${attempt}/30"
done

info "Smoke test failed; server logs:"
cat /tmp/pdf_vision_smoke.log
exit 1

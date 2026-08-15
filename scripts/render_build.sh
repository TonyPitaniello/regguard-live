#!/usr/bin/env bash
# Resilient Render build — survives transient PyPI 502s.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$ROOT/backend/requirements.txt"
if [[ ! -f "$REQ" ]]; then
  # rootDir=backend on some Render configs
  REQ="$ROOT/requirements.txt"
fi
if [[ ! -f "$REQ" ]]; then
  echo "ERROR: requirements.txt not found (tried backend/ and .)" >&2
  exit 1
fi

echo "Using requirements: $REQ"
python -m pip install --upgrade pip

# Retries for files.pythonhosted.org 502s (common on Render cache-clear builds)
ATTEMPTS=5
DELAY=8
for i in $(seq 1 "$ATTEMPTS"); do
  echo "pip install attempt $i/$ATTEMPTS..."
  if python -m pip install \
      --default-timeout=100 \
      --retries=10 \
      --no-cache-dir \
      -r "$REQ"; then
    echo "pip install succeeded"
    exit 0
  fi
  echo "pip install failed (attempt $i). Waiting ${DELAY}s..."
  sleep "$DELAY"
  DELAY=$((DELAY * 2))
done

echo "ERROR: pip install failed after $ATTEMPTS attempts" >&2
exit 1

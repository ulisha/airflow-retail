#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATALENS_DIR="${DATALENS_DIR:-$ROOT_DIR/.local/datalens}"

if [ ! -d "$DATALENS_DIR" ]; then
  echo "Local DataLens directory does not exist: $DATALENS_DIR"
  exit 0
fi

cd "$DATALENS_DIR"
docker compose down

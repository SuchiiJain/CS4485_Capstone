#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8010}"
TOKEN="${DOCROT_API_TOKEN:-}"
DB_PATH="${DOCROT_DB_PATH:-}"

export DOCROT_API_PORT="$PORT"
export DOCROT_API_TOKEN="$TOKEN"
if [[ -n "$DB_PATH" ]]; then
  export DOCROT_DB_PATH="$DB_PATH"
fi

echo "Starting Docrot API on port ${DOCROT_API_PORT}..."
python -m src.api_server

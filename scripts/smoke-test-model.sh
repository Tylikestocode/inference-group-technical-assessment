#!/bin/sh

set -eu

MODEL_NAME="qwen3.5:9b"
PROMPT="Reply with one short sentence confirming that the local model is ready."

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
ERROR_LOG=$(mktemp "${TMPDIR:-/tmp}/model-smoke.XXXXXX")

trap 'rm -f "$ERROR_LOG"' EXIT HUP INT TERM

compose() {
  docker compose -f "$PROJECT_DIR/compose.yaml" "$@"
}

if ! docker info >/dev/null 2>&1; then
  echo "The Docker daemon is not running. Start Docker and try again." >&2
  exit 1
fi

if ! compose ps --status running --services | grep -qx "ollama"; then
  echo "Ollama is not running. Run ./scripts/setup-model.sh first." >&2
  exit 1
fi

echo "Sending a prompt to $MODEL_NAME through http://ollama:11434..."
if ! response=$(
  compose --profile tools run --rm --no-deps -T ollama-cli \
    run --think=false --nowordwrap "$MODEL_NAME" "$PROMPT" 2>"$ERROR_LOG"
); then
  cat "$ERROR_LOG" >&2
  exit 1
fi

if [ -z "$(printf '%s' "$response" | tr -d '[:space:]')" ]; then
  echo "The model returned an empty response." >&2
  exit 1
fi

printf '%s\n' "$response"

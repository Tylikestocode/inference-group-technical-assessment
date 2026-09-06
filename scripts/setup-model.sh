#!/bin/sh

set -eu

MODEL_NAME="qwen3.5:9b"
MAX_ATTEMPTS=30
RETRY_DELAY_SECONDS=2

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")

compose() {
  docker compose -f "$PROJECT_DIR/compose.yaml" "$@"
}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but was not found." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required but is not available." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "The Docker daemon is not running. Start Docker and try again." >&2
  exit 1
fi

echo "Starting Ollama..."
compose up -d ollama

attempt=1
while ! compose --profile tools run --rm --no-deps -T ollama-cli list >/dev/null 2>&1; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "Ollama did not become ready within $((MAX_ATTEMPTS * RETRY_DELAY_SECONDS)) seconds." >&2
    compose logs ollama >&2
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep "$RETRY_DELAY_SECONDS"
done

echo "Pulling $MODEL_NAME. The first download is approximately 6.6 GB."
compose --profile tools run --rm --no-deps -T ollama-cli pull "$MODEL_NAME"

echo "Installed models:"
compose --profile tools run --rm --no-deps -T ollama-cli list

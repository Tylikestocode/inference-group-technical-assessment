# Model Serving Task 001: Start Qwen with Docker Compose

- Status: Done
- Slice: 1 - Runnable foundation
- Size: Small
- Related ADRs: ADR-004, ADR-006

## Outcome

Qwen 3.5 9B can be started locally as part of the containerized solution.

## Work

- Add an Ollama service to Docker Compose.
- Persist downloaded model data in a named volume.
- Add a setup command or script that pulls `qwen3.5:9b`.
- Document hardware and first-download expectations.

## Acceptance criteria

- Docker Compose starts Ollama successfully.
- The model remains available after the service is restarted.
- A simple local prompt receives a response from `qwen3.5:9b`.
- The application service can reach Ollama by its Compose service name.

## Not included

- GPU tuning for every platform
- Production model autoscaling
- Additional language models

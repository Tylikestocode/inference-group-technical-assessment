# Model Serving Task 003: Add readiness and graceful fallback

- Status: Planned
- Slice: 3 - Safe and demonstrable prototype
- Size: Small
- Depends on: Model Serving Task 002
- Related ADRs: ADR-004, ADR-006, ADR-017

## Outcome

The application starts predictably and remains safe when Qwen is slow, unavailable, or returns an invalid result.

## Work

- Add an Ollama health or readiness check to Docker Compose.
- Enforce a model-call timeout.
- Convert connection, timeout, and invalid-response failures into typed results.
- Add tests for each failure using a stand-in adapter.
- Document how to demonstrate the model-offline fallback.

## Acceptance criteria

- Service readiness is visible through Docker Compose.
- A model timeout does not crash or stall the investigation indefinitely.
- Model failures reach the agent's deterministic fallback route.
- Failure tests do not require the real model.

## Not included

- Automatic provider failover
- Model performance benchmarking
- Production traffic management

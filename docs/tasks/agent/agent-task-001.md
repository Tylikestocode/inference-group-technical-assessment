# Agent Task 001: Define the controlled workflow

- Status: Planned
- Slice: 1 - Runnable foundation
- Size: Small
- Depends on: API Task 001
- Related ADRs: ADR-002, ADR-009, ADR-010, ADR-012

## Outcome

The investigation has a clear LangGraph structure and validated state before external services are connected.

## Work

- Define the workflow state and final response models.
- Add named steps for transaction lookup, procedure retrieval, decision checks, explanation, and validation.
- Define success, escalation, and failure routes.
- Accept only requests that have already passed deterministic transaction-ID validation.

## Acceptance criteria

- The graph can be created and run with simple stand-in services.
- Every step has one stated responsibility.
- Failure routes end in a valid response instead of an unhandled exception.
- The graph contains no model-controlled tool loop.

## Not included

- Live API, FAISS, or Ollama calls
- Final business rules
- Multi-agent behavior

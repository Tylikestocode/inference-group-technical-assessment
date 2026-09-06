# Agent Task 003: Add safe failure and fallback routes

- Status: Done
- Slice: 3 - Safe and demonstrable prototype
- Size: Medium
- Depends on: Agent Task 002, API Task 003, Retrieval Task 003, Model Serving Task 003
- Related ADRs: ADR-010, ADR-012, ADR-015, ADR-016, ADR-017

## Outcome

The agent returns a cautious, structured result whenever it cannot complete a reliable investigation.

## Work

- Handle unknown transactions, API failures, missing procedures, and model failures.
- Require human review for held, high-risk, sanctions-related, or uncertain cases.
- Reject recommendations outside the permitted action list.
- Add a deterministic explanation when the model is unavailable.
- Add workflow tests using predictable stand-in services.

## Acceptance criteria

- Each planned failure reaches a named outcome with no invented facts.
- The model cannot release, approve, reject, or alter a transaction.
- Model failure still returns verified facts, procedure guidance when available, and an escalation decision.
- Core agent tests pass without running Docker or Ollama.

## Not included

- Automatic retries beyond one controlled attempt
- Human approval user interface
- Production audit storage

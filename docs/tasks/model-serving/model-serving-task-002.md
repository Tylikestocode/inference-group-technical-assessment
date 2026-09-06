# Model Serving Task 002: Implement the replaceable model adapter

- Status: Planned
- Slice: 2 - Complete TXN-0212 investigation
- Size: Small
- Depends on: Model Serving Task 001
- Related ADRs: ADR-004, ADR-005, ADR-010, ADR-015

## Outcome

The agent can request a short explanation from Qwen without depending directly on Ollama-specific code.

## Work

- Define the application interface for generating an investigation explanation.
- Implement the Ollama adapter behind that interface.
- Provide only verified transaction facts, retrieved procedure text, and the predetermined next action.
- Request and validate a small structured model response.
- Keep model address, model name, timeout, and generation settings configurable.

## Acceptance criteria

- The adapter returns a validated explanation for the `TXN-0212` context.
- Qwen is not asked to select tools or decide whether escalation is required.
- Ollama-specific details do not appear in the agent workflow.
- A stand-in adapter can replace Ollama in tests.

## Not included

- Fine-tuning
- Prompt optimization beyond the main scenario
- Direct access from the model to the transaction API

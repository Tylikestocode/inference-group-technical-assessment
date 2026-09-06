# Agent Task 002: Complete the TXN-0212 happy path

- Status: Planned
- Slice: 2 - Complete TXN-0212 investigation
- Size: Medium
- Depends on: Agent Task 001, API Task 002, Retrieval Task 002, Model Serving Task 002
- Related ADRs: ADR-002, ADR-005, ADR-012, ADR-015, ADR-016

## Outcome

The workflow produces a grounded, structured investigation for `TXN-0212`.

## Work

- Call the transaction API with the validated ID.
- Build a procedure-search query from the advisor question and verified transaction facts.
- Retrieve and retain the best procedure references.
- Apply deterministic escalation and allowed-action rules.
- Ask the model adapter to explain the verified result.
- Assemble and validate the final response in application code.

## Acceptance criteria

- `TXN-0212` completes every happy-path workflow step.
- The transaction facts come from the API and the procedure comes from retrieval.
- The application, not the model, sets escalation and permitted next action.
- The final response contains all fields required by the assessment.

## Not included

- Failure recovery
- Conversation memory
- Actions that change a transaction

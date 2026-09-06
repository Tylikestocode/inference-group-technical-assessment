# CLI Task 002: Display the complete investigation

- Status: Planned
- Slice: 2 - Complete TXN-0212 investigation
- Size: Small
- Depends on: CLI Task 001, Agent Task 002
- Related ADRs: ADR-010, ADR-011, ADR-016

## Outcome

An advisor can investigate `TXN-0212` with one command and understand the result without reading raw system data.

## Work

- Connect the `investigate` command to the agent workflow.
- Display transaction status, hold reason, relevant procedure, next action, and escalation requirement.
- Clearly label the content as fictional assessment data.
- Keep the terminal output concise and readable.

## Acceptance criteria

- `bank-ops investigate "Why is TXN-0212 held?"` runs end to end.
- All required response fields are visible.
- The displayed facts match the API result.
- The procedure used by the agent is named in the output.

## Not included

- A web interface
- Transaction actions or approvals
- Multi-turn conversation

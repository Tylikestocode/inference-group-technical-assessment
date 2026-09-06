# CLI Task 003: Add JSON output and demo-friendly errors

- Status: Done
- Slice: 3 - Safe and demonstrable prototype
- Size: Small
- Depends on: CLI Task 002, Agent Task 003
- Related ADRs: ADR-006, ADR-011, ADR-016

## Outcome

The CLI is easy to demonstrate in both human-readable and structured modes, including failure cases.

## Work

- Add a `--json` option using the same validated response as the normal view.
- Map invalid input and system failures to clear messages and non-zero exit codes.
- Add a short demo command or documented command sequence.
- Ensure the CLI works through Docker Compose and direct uv execution.

## Acceptance criteria

- JSON output is valid and contains the required response fields.
- Unknown transaction and unavailable-service cases are clearly distinguishable.
- No stack trace is shown for an expected business failure.
- The documented demo commands work from a clean setup.

## Not included

- Shell completion
- Saved conversations
- Advanced terminal styling

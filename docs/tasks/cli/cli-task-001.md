# CLI Task 001: Create the command-line entry point

- Status: Planned
- Slice: 1 - Runnable foundation
- Size: Small
- Related ADRs: ADR-003, ADR-010, ADR-011

## Outcome

A reviewer can run the application, see available commands, and receive immediate feedback for an invalid transaction question.

## Work

- Add the `bank-ops` command and help text.
- Add configuration loading for service addresses and model names.
- Add the `investigate` command with a question argument.
- Extract and validate exactly one `TXN-0000` style transaction ID before calling the agent.

## Acceptance criteria

- `bank-ops --help` lists the supported commands.
- A request containing one valid ID is passed to the agent boundary.
- Missing, malformed, or multiple IDs return clear guidance.
- Invalid input does not call the API, retriever, or model.

## Not included

- Full investigation output
- JSON output
- Interactive chat history

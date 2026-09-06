# API Task 001: Define the transaction service contract

- Status: Planned
- Slice: 1 - Runnable foundation
- Size: Small
- Related ADRs: ADR-001, ADR-010, ADR-013

## Outcome

The project has one agreed transaction format and a small set of fictional records for development and testing.

## Work

- Define the transaction request, response, and error formats with Pydantic.
- Create fictional JSON records, including `TXN-0212` and an unknown-ID case.
- Include status, amount, currency, risk level, hold reason, channel, and timestamp.
- Add a read-only repository that loads and validates the JSON data.

## Acceptance criteria

- `TXN-0212` can be loaded as a valid typed transaction.
- Invalid fixture data causes a clear startup or test failure.
- Looking up an unknown ID produces a specific not-found result.
- No real customer or bank data is included.

## Not included

- HTTP endpoints
- PostgreSQL
- Transaction updates

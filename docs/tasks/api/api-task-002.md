# API Task 002: Expose the transaction lookup endpoint

- Status: Done
- Slice: 2 - Complete TXN-0212 investigation
- Size: Small
- Depends on: API Task 001
- Related ADRs: ADR-005, ADR-010, ADR-013

## Outcome

The agent can retrieve a fictional transaction through a read-only API.

## Work

- Add a small Python API service with `GET /transactions/{transaction_id}`.
- Connect the endpoint to the JSON transaction repository.
- Return a typed transaction for a known ID and a clear `404` response for an unknown ID.
- Add a client interface that the agent can call without depending directly on the API framework.

## Acceptance criteria

- Requesting `TXN-0212` returns the expected transaction data.
- Requesting `TXN-9999` returns `404` without invented details.
- The endpoint cannot create or change a transaction.
- API and client contract tests pass.

## Not included

- Authentication
- Write endpoints
- Production banking integrations

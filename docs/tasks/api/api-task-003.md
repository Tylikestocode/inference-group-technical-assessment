# API Task 003: Add health checks and safe API failures

- Status: Done
- Slice: 3 - Safe and demonstrable prototype
- Size: Small
- Depends on: API Task 002
- Related ADRs: ADR-006, ADR-013, ADR-017

## Outcome

The transaction service is observable in Docker Compose and its failure behavior is predictable.

## Work

- Add a lightweight health endpoint.
- Add request timeouts and clear unavailable-service errors to the API client.
- Provide one controlled way to demonstrate a service failure.
- Add the API service and its health check to Docker Compose.

## Acceptance criteria

- Docker Compose reports whether the API is healthy.
- The agent receives a typed error when the service is stopped or times out.
- The failure demonstration does not require changing source code.
- Automated tests cover healthy, not-found, and unavailable cases.

## Not included

- Production monitoring
- Automatic scaling
- Persistent database storage

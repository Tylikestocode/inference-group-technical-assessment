# Retrieval Task 001: Create the procedure corpus

- Status: Done
- Slice: 1 - Runnable foundation
- Size: Small
- Related ADRs: ADR-008, ADR-014

## Outcome

The project has four short, understandable procedures that cover the planned demonstration scenarios.

## Work

- Write the sanctions-screening procedure.
- Write the high-value and unusual-activity procedure.
- Write the beneficiary-verification procedure used by `TXN-0212`.
- Write the manual-review and escalation procedure.
- Give each document an ID, title, version, owner, and fictional-data label.

## Acceptance criteria

- Exactly four Markdown procedure files exist.
- Each procedure states when it applies, what the advisor should do, and when to escalate.
- The `TXN-0212` hold reason has an unambiguous matching section.
- The documents contain no real bank policy or customer data.

## Not included

- Embeddings
- FAISS index creation
- Production policy approval

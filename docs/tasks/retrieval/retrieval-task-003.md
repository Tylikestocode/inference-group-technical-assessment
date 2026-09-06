# Retrieval Task 003: Add retrieval safeguards and checks

- Status: Done
- Slice: 3 - Safe and demonstrable prototype
- Size: Small
- Depends on: Retrieval Task 002
- Related ADRs: ADR-007, ADR-008, ADR-014, ADR-017

## Outcome

The retriever can distinguish useful procedure matches from cases that require human escalation.

## Work

- Add a minimum relevance setting and a no-relevant-procedure result.
- Record the embedding model and source-document fingerprint with the index.
- Refuse to load an index built with incompatible settings or outdated source documents.
- Add small retrieval checks for all four procedures and one unrelated query.
- Mount or persist the built index through Docker Compose.

## Acceptance criteria

- Expected example queries return the intended procedure.
- An unrelated query does not produce confident policy guidance.
- A missing, stale, or incompatible index produces a clear recovery instruction.
- Retrieval tests use the fixed fictional corpus and do not call Ollama.

## Not included

- Formal production retrieval evaluation
- Access-controlled document filtering
- Automatic document synchronization

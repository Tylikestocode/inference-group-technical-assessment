# Retrieval Task 002: Build and query the FAISS index

- Status: Done
- Slice: 2 - Complete TXN-0212 investigation
- Size: Medium
- Depends on: Retrieval Task 001
- Related ADRs: ADR-005, ADR-007, ADR-008

## Outcome

The application can build a local search index and retrieve the beneficiary-verification procedure for `TXN-0212`.

## Work

- Load and split the four Markdown procedures while preserving document and section details.
- Create embeddings with `BAAI/bge-small-en-v1.5`.
- Build and save the FAISS index inside the application environment.
- Save the matching text and procedure details needed for citations.
- Add a retriever interface and query implementation.

## Acceptance criteria

- One command rebuilds the index from the four source documents.
- A query based on the `TXN-0212` hold returns the beneficiary-verification procedure first.
- Search results include procedure ID, title, version, section, source file, and relevance score.
- Rebuilding from unchanged documents produces a usable index.

## Not included

- Keyword or hybrid search
- A remote vector database
- Large-scale retrieval performance testing

# Architecture Decision Records

These records capture the key technical decisions for the AI Operations Agent. Each decision is accepted for the prototype unless a later ADR replaces it.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](ADR-001.md) | Use Python as the main language | Accepted |
| [ADR-002](ADR-002.md) | Use LangGraph for the agent workflow | Accepted |
| [ADR-003](ADR-003.md) | Use uv for dependency management | Accepted |
| [ADR-004](ADR-004.md) | Use Ollama for local model serving | Accepted |
| [ADR-005](ADR-005.md) | Keep model and inference providers replaceable | Accepted |
| [ADR-006](ADR-006.md) | Package the solution with Docker Compose | Accepted |
| [ADR-007](ADR-007.md) | Use FAISS for local vector retrieval | Accepted |
| [ADR-008](ADR-008.md) | Use a Hugging Face embedding model | Accepted |
| [ADR-009](ADR-009.md) | Extract transaction IDs before the agent workflow | Accepted |
| [ADR-010](ADR-010.md) | Use Pydantic for typing and validation | Accepted |
| [ADR-011](ADR-011.md) | Provide a command-line interface | Accepted |
| [ADR-012](ADR-012.md) | Use one controlled agent workflow | Accepted |
| [ADR-013](ADR-013.md) | Use a synthetic transaction repository | Accepted |
| [ADR-014](ADR-014.md) | Use four Markdown procedure documents | Accepted |
| [ADR-015](ADR-015.md) | Keep operational decisions deterministic | Accepted |
| [ADR-016](ADR-016.md) | Return structured, traceable responses | Accepted |
| [ADR-017](ADR-017.md) | Test without requiring live AI services | Accepted |

## ADR lifecycle

Accepted ADRs are not rewritten when a decision changes. A new ADR should be added and the older record marked `Superseded by ADR-XXX`.

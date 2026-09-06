# High-Level Architecture Overview

```mermaid
flowchart LR
    A[CLI]
    B[API]
    C[Agent]
    D[Ollama - Qwen]
    E[Tools]
    F[Faiss Index]

    A --> B
    B --> C
    C --> D
    C --> E
    E --> F
```

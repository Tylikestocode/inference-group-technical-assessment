# Deployment architecture

This diagram shows the local prototype deployment defined by the accepted architecture decisions. All transaction and procedure data is fictional and remains inside the Docker Compose environment.

```mermaid
flowchart LR
    advisor["Bank advisor"]

    subgraph host["Reviewer's workstation"]
        terminal["Terminal"]

        subgraph compose["Docker Compose"]
            subgraph app["Application container · Python"]
                cli["bank-ops CLI"]
                workflow["LangGraph investigation workflow"]
                rules["Deterministic validation<br/>and escalation rules"]
                retrieval["Procedure retriever<br/>BGE embeddings + FAISS"]
                model_adapter["Model adapter"]
                api_client["Transaction API client"]

                cli --> workflow
                workflow --> rules
                workflow --> retrieval
                workflow --> model_adapter
                workflow --> api_client
            end

            subgraph transaction_service["Transaction API container · Python"]
                api["Read-only<br/>GET /transactions/{id}"]
                repository["JSON repository"]
                api --> repository
            end

            subgraph model_service["Model-serving container"]
                ollama["Ollama"]
                qwen["Qwen 3.5 9B"]
                ollama --> qwen
            end

            procedures[("Four Markdown<br/>procedure documents")]
            faiss_volume[("Persistent FAISS<br/>index volume")]
            model_volume[("Persistent Ollama<br/>model volume")]

            api_client -->|"HTTP · read only"| api
            retrieval -->|"read"| procedures
            retrieval <-->|"build / query"| faiss_volume
            model_adapter -->|"HTTP · verified context only"| ollama
            qwen --- model_volume
        end

        terminal -->|"docker compose / uv command"| cli
    end

    advisor -->|"transaction question"| terminal
    cli -->|"validated investigation result"| terminal
    terminal -->|"human-readable or JSON response"| advisor

    classDef person fill:#fef3c7,stroke:#b45309,color:#451a03
    classDef boundary fill:#eff6ff,stroke:#2563eb,color:#172554
    classDef service fill:#ecfdf5,stroke:#059669,color:#022c22
    classDef store fill:#f5f3ff,stroke:#7c3aed,color:#2e1065

    class advisor person
    class terminal boundary
    class cli,workflow,rules,retrieval,model_adapter,api_client,api,repository,ollama,qwen service
    class procedures,faiss_volume,model_volume store
```

## Deployment notes

- The CLI, controlled workflow, deterministic business rules, and provider adapters run in one application container.
- The transaction API is a separate read-only service backed by synthetic JSON data.
- Procedure retrieval runs locally in the application container; the FAISS index is persisted in a named volume and can be rebuilt from the four Markdown source documents.
- Ollama serves `qwen3.5:9b` over the internal Compose network and keeps downloaded model data in a named volume.
- Qwen receives only verified transaction facts, retrieved procedure guidance, and the application-determined next action. It cannot call services or change a transaction.
- If Ollama is unavailable, the application returns a deterministic explanation from the verified facts and rules.

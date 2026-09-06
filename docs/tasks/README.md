# Implementation Task Map

This folder breaks the AI Operations Agent into small tasks across five context boundaries:

- `cli` - commands and advisor-facing output
- `api` - read-only synthetic transaction service
- `agent` - controlled investigation workflow and business rules
- `model-serving` - Ollama, Qwen, and the model adapter
- `retrieval` - procedure documents, embeddings, and FAISS search

The API is a small Python HTTP service backed by fictional JSON data. It demonstrates the required transaction tool without introducing a production database.

## Delivery approach

Complete the work as three vertical slices. A slice is complete only when its behavior can be run or tested from the outside.

### Slice 1 - Runnable foundation

Goal: start the services, validate a transaction number, and prove that every boundary has a working entry point.

1. [model-serving-task-001](model-serving/model-serving-task-001.md)
2. [api-task-001](api/api-task-001.md)
3. [retrieval-task-001](retrieval/retrieval-task-001.md)
4. [agent-task-001](agent/agent-task-001.md)
5. [cli-task-001](cli/cli-task-001.md)

### Slice 2 - Complete TXN-0212 investigation

Goal: run one command that retrieves `TXN-0212`, finds the relevant procedure, uses Qwen to explain the result, and displays the required response.

1. [api-task-002](api/api-task-002.md)
2. [retrieval-task-002](retrieval/retrieval-task-002.md)
3. [model-serving-task-002](model-serving/model-serving-task-002.md)
4. [agent-task-002](agent/agent-task-002.md)
5. [cli-task-002](cli/cli-task-002.md)

### Slice 3 - Safe and demonstrable prototype

Goal: handle important failures, return predictable output, and make the complete solution easy to demonstrate with Docker Compose.

1. [api-task-003](api/api-task-003.md)
2. [retrieval-task-003](retrieval/retrieval-task-003.md)
3. [model-serving-task-003](model-serving/model-serving-task-003.md)
4. [agent-task-003](agent/agent-task-003.md)
5. [cli-task-003](cli/cli-task-003.md)

## Task status

All tasks begin with status `Planned`. Change a task to `In progress`, `Blocked`, or `Done` as work proceeds.

## Prototype definition of done

- Docker Compose starts the required services.
- One CLI command investigates `TXN-0212` from end to end.
- The answer includes transaction status, relevant procedure, next action, and escalation requirement.
- Unknown transactions, unavailable services, and missing procedures fail safely.
- Core tests run without requiring a live model.
- The README contains setup and demonstration instructions.

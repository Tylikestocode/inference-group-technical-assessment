# Inference Group Technical Assessment

This repository contains a local AI Operations Agent prototype. The first
runtime component is Qwen 3.5 9B served by Ollama through Docker Compose.

## Python development

The application uses Python 3.12 and [uv](https://docs.astral.sh/uv/) for
dependency management. Install the locked development environment and run the
automated tests from the repository root:

```sh
uv sync --locked
uv run pytest
```

The tests use packaged fictional transaction records and do not require Ollama
or another live service.

## Run the transaction API

Start the read-only synthetic transaction service directly from the repository
root:

```sh
uv run uvicorn bank_ops.transactions.api:app --host 127.0.0.1 --port 8000
```

Look up a known or unknown transaction in another terminal:

```sh
curl --fail-with-body http://127.0.0.1:8000/transactions/TXN-0212
curl --fail-with-body http://127.0.0.1:8000/transactions/TXN-9999
```

The service exposes no endpoints for creating or changing transactions.

To run the API through Docker Compose instead, build it and wait for its health
check to pass:

```sh
docker compose up -d --build --wait api
docker compose ps api
curl --fail-with-body http://127.0.0.1:8000/health
```

Docker Compose reports the service as `healthy` after `/health` responds. A
controlled unavailable-service result can be demonstrated without changing
source code by stopping only the API and calling the application-owned client:

```sh
docker compose stop api
uv run python -c 'from bank_ops.transactions import HttpTransactionClient, TransactionLookupRequest; result = HttpTransactionClient("http://127.0.0.1:8000").get(TransactionLookupRequest(transaction_id="TXN-0212")); print(result.model_dump_json())'
docker compose start --wait api
```

The stopped-service call prints a typed
`transaction_service_unavailable` result. The client timeout defaults to five
seconds and can be changed with `BANK_OPS_TRANSACTION_TIMEOUT_SECONDS`.

## Command-line interface

Show the available commands or submit a transaction question:

```sh
uv run bank-ops --help
uv run bank-ops investigate "Why is TXN-0212 held?"
uv run bank-ops investigate "Why is TXN-0212 held?" --json
```

Questions must contain exactly one case-sensitive transaction ID in the form
`TXN-0000`. Invalid questions are rejected before any API, retriever, or model
is initialized.

`--json` serializes the same validated investigation response used by the
readable view. This keeps exact monetary values, timestamps, procedure citation
details, warnings, and the trace ID available to scripts.

The command uses stable exit codes so demonstrations and scripts can distinguish
outcomes:

| Exit code | Meaning |
| ---: | --- |
| `0` | Investigation completed, including a safe model fallback |
| `1` | The CLI could not start or complete the operation |
| `2` | Invalid command input or configuration |
| `3` | Transaction was not found |
| `4` | Transaction service was unavailable |
| `5` | No relevant procedure was available |

Expected failure responses are still printed in full (as readable text or valid
JSON) before the command exits. Operational startup failures are written to
standard error without a traceback.

The investigation is displayed as a concise advisor-facing summary. All data in
the prototype is fictional assessment data. A successful `TXN-0212` run has the
following shape (the explanation and trace ID are generated at runtime):

```text
=== Fictional assessment data ===
Transaction: TXN-0212
Status: held
Hold reason: Beneficiary details do not match the payment instruction.
Outcome: escalation required

Relevant procedure:
  PROC-003 — Beneficiary Verification (version 1.0)
  Section: Beneficiary details do not match the payment instruction

Explanation: The transaction is held because the beneficiary details do not match the payment instruction.
Next action: Compare the available beneficiary details with the original payment instruction, keep the transaction held, and refer any unresolved mismatch to Fictional Payments Operations.
Human review required: Yes
Escalation destination: Fictional Payments Operations
Warnings:
  - This agent is advisory and cannot release, approve, reject, edit, or bypass the transaction.
Trace ID: 12345678-1234-5678-1234-567812345678
```

### Short demo sequence

From a clean checkout, prepare the locked environment and local services, then
run the readable, JSON, and unknown-transaction cases:

```sh
uv sync --locked
docker compose up -d --build --wait api
./scripts/setup-model.sh
uv run bank-ops build-index
uv run bank-ops investigate "Why is TXN-0212 held?"
uv run bank-ops investigate "Why is TXN-0212 held?" --json
uv run bank-ops investigate "Why is TXN-9999 held?" --json
```

The final command returns exit code `3` and an outcome of
`transaction_not_found`. Stop the API to demonstrate the distinguishable
unavailable-service response, which returns exit code `4`, then restore it:

```sh
docker compose stop api
uv run bank-ops investigate "Why is TXN-0212 held?" --json
docker compose start --wait api
```

To run the investigation CLI inside Docker Compose using the same persisted
procedure index:

```sh
docker compose --profile tools build procedure-index cli
docker compose --profile tools run --rm procedure-index
docker compose --profile tools run --rm cli investigate "Why is TXN-0212 held?" --json
```

The `cli` service uses Compose service addresses for the transaction API and
Ollama, while direct `uv run` commands use the host addresses from `.env` or
their defaults.

Runtime configuration can be supplied through a `.env` file or environment
variables. Copy `.env.example` to see the available `BANK_OPS_*` settings and
their local-development values.

## Procedure search index

Build the local procedure index from the four packaged Markdown procedures:

```sh
uv run bank-ops build-index
```

The first build downloads `BAAI/bge-small-en-v1.5`. Later builds reuse the
local Hugging Face cache. The generated FAISS index and its citation metadata
are written to `var/retrieval/` by default; set
`BANK_OPS_PROCEDURE_INDEX_DIR` to use another application-local directory.
Search results must meet `BANK_OPS_MINIMUM_RELEVANCE_SCORE`, which defaults to
`0.6`. If no result meets that threshold, retrieval returns a specific
no-relevant-procedure result so the investigation can be sent for human review
without presenting a weak match as policy guidance.

The citation manifest records its embedding model and a SHA-256 fingerprint of
the exact source documents. A missing index, a different configured embedding
model, or changed procedure source causes loading to fail with an instruction
to rebuild the index:

```sh
uv run bank-ops build-index
```

To build inside Docker Compose and persist the artifacts in the named
`procedure_index_data` volume, run:

```sh
docker compose --profile tools build procedure-index
docker compose --profile tools run --rm procedure-index
```

The index remains in the volume after `docker compose down`. Running
`docker compose down -v` removes it and requires another build.

Run the deterministic retrieval tests without downloading a model:

```sh
uv run pytest tests/retrieval
```

To exercise the real embedding model, check all four expected procedure
queries, and confirm that an unrelated query is rejected, run:

```sh
RUN_RETRIEVAL_INTEGRATION=1 uv run pytest -m retrieval_integration
```

## Investigation workflow integration

The default test suite exercises the complete controlled workflow with local
stand-ins. To run the same `TXN-0212` path through the transaction API, FAISS
index, and Ollama adapters, start the services, build the index, and enable the
opt-in integration test:

```sh
uv run uvicorn bank_ops.transactions.api:app
./scripts/setup-model.sh
uv run bank-ops build-index
RUN_AGENT_INTEGRATION=1 uv run pytest tests/test_workflow_integration.py
```

Run the API command in a separate terminal. The workflow returns a validated
structured response; advisor-facing rendering is added in CLI Task 002.

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- A practical minimum of 24 GB of system memory
- At least 12 GB of free disk space for the Ollama image and model data

When using Docker Desktop, allocate at least 12 GB of memory to its Linux VM;
16 GB is recommended. An 8 GB Docker memory limit is not sufficient to load
this model reliably, even when the host has additional free memory.

The default configuration is a portable CPU-only baseline. Inference speed and
hardware acceleration vary by operating system and hardware; platform-specific
GPU tuning is outside the scope of this prototype.

The `qwen3.5:9b` model download is approximately 6.6 GB. The first setup can
therefore take several minutes, depending on the network connection. The first
prompt after startup can also be slower while Ollama loads the model into
memory.

## Set up the model

Run the setup script from the repository root:

```sh
./scripts/setup-model.sh
```

The script starts Ollama, waits for Docker Compose to report it healthy, and
downloads `qwen3.5:9b`. It is safe to run the command again; Ollama reuses the
downloaded model data.

Run a live smoke test:

```sh
./scripts/smoke-test-model.sh
```

To exercise the application adapter itself against the installed model, run:

```sh
BANK_OPS_RUN_MODEL_INTEGRATION=1 uv run pytest -m integration \
  tests/model_serving/test_ollama_integration.py
```

This test sends the fictional `TXN-0212` facts, the retrieved `PROC-003` text,
and a predetermined next action to Qwen, then validates its structured reply.
The normal test suite skips this opt-in integration test.

The smoke test sends a prompt from a Compose helper container to
`http://ollama:11434`. This is the same service-name address that the
containerized application will use. From the host machine, the API is available
at `http://localhost:11434`.

## Operate Ollama

Start or stop the service independently:

```sh
docker compose up -d --wait ollama
docker compose stop ollama
```

Inspect its health and logs:

```sh
docker compose ps
docker compose logs -f ollama
```

## Demonstrate the model-offline fallback

First start the transaction API in a separate terminal:

```sh
uv run uvicorn bank_ops.transactions.api:app --host 127.0.0.1 --port 8000
```

Then build the procedure index and make sure the normal local model setup has
completed:

```sh
uv run bank-ops build-index
./scripts/setup-model.sh
```

Docker Compose should report Ollama as healthy. Stop only the model service,
then run the same investigation command:

```sh
docker compose ps ollama
docker compose stop ollama
uv run bank-ops investigate "Why is TXN-0212 held?"
```

The investigation still returns the verified transaction, cited procedure,
predetermined next action, and human-review decision. Its explanation uses
deterministic wording and its warnings state that the model explanation was
unavailable. No source changes or live model are required for this route.

Restart Ollama and wait for readiness before continuing normal demonstrations:

```sh
docker compose up -d --wait ollama
./scripts/smoke-test-model.sh
```

Restart Ollama and confirm that the model remains installed:

```sh
docker compose restart ollama
docker compose --profile tools run --rm --no-deps -T ollama-cli list
./scripts/smoke-test-model.sh
```

Stop and remove the containers while retaining the downloaded model:

```sh
docker compose down
```

The model is stored in the named `ollama_data` volume and remains available
after container or service restarts. To remove the model data as well, run
`docker compose down -v`. The next setup will download the model again.

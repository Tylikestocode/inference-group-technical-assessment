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

## Command-line interface

Show the available commands or submit a transaction question:

```sh
uv run bank-ops --help
uv run bank-ops investigate "Why is TXN-0212 held?"
```

Questions must contain exactly one case-sensitive transaction ID in the form
`TXN-0000`. Invalid questions are rejected before any API, retriever, or model
is initialized.

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

Run the deterministic retrieval tests without downloading a model:

```sh
uv run pytest tests/retrieval
```

To exercise the real embedding model and confirm that the `TXN-0212` hold
reason returns the Beneficiary Verification procedure first, run:

```sh
RUN_RETRIEVAL_INTEGRATION=1 uv run pytest -m retrieval_integration
```

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

The script starts Ollama, waits for it to accept connections, and downloads
`qwen3.5:9b`. It is safe to run the command again; Ollama reuses the downloaded
model data.

Run a live smoke test:

```sh
./scripts/smoke-test-model.sh
```

The smoke test sends a prompt from a Compose helper container to
`http://ollama:11434`. This is the same service-name address that the
containerized application will use. From the host machine, the API is available
at `http://localhost:11434`.

## Operate Ollama

Start or stop the service independently:

```sh
docker compose up -d ollama
docker compose stop ollama
```

Inspect its state and logs:

```sh
docker compose ps
docker compose logs -f ollama
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

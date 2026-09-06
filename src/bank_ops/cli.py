"""Command-line entry point for the AI Operations Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Protocol

import typer
from pydantic import ValidationError

from bank_ops.investigations import (
    InvestigationRequest,
    InvestigationResponse,
    TransactionQuestionError,
)
from bank_ops.retrieval import HuggingFaceBgeEmbedder, build_procedure_index
from bank_ops.settings import Settings
from bank_ops.workflow import create_investigation_workflow


class AgentBoundary(Protocol):
    """Callable boundary that accepts a validated investigation request."""

    def __call__(self, request: InvestigationRequest) -> InvestigationResponse:
        """Submit an investigation and return its validated result."""


class AgentFactory(Protocol):
    """Create the agent boundary from validated application settings."""

    def __call__(self, settings: Settings) -> AgentBoundary:
        """Build the boundary without exposing service details to the CLI."""


SettingsLoader = Callable[[], Settings]
IndexBuilder = Callable[[Settings], int]


def create_procedure_index(settings: Settings) -> int:
    """Build the configured procedure index with the selected embedding model."""

    embedder = HuggingFaceBgeEmbedder(settings.embedding_model)
    return build_procedure_index(embedder, settings.procedure_index_dir)


def create_app(
    agent_factory: AgentFactory = create_investigation_workflow,
    settings_loader: SettingsLoader = Settings,
    index_builder: IndexBuilder = create_procedure_index,
) -> typer.Typer:
    """Build the CLI with injectable edges for deterministic tests."""

    cli = typer.Typer(
        help="Investigate fictional held transactions safely.",
        no_args_is_help=True,
        pretty_exceptions_show_locals=False,
    )

    @cli.callback()
    def main() -> None:
        """Investigate fictional held transactions safely."""

    @cli.command()
    def build_index() -> None:
        """Rebuild the local FAISS procedure index from packaged Markdown."""

        settings = _load_settings(settings_loader)
        chunk_count = index_builder(settings)
        typer.echo(
            f"Built {chunk_count} procedure sections in {settings.procedure_index_dir}."
        )

    @cli.command()
    def investigate(
        question: Annotated[
            str,
            typer.Argument(
                help='Transaction question, for example "Why is TXN-0212 held?".'
            ),
        ],
    ) -> None:
        """Validate a transaction question and submit it for investigation."""

        try:
            request = InvestigationRequest.from_question(question)
        except TransactionQuestionError as error:
            raise typer.BadParameter(str(error), param_hint="QUESTION") from error

        settings = _load_settings(settings_loader)

        agent = agent_factory(settings)
        typer.echo(format_investigation_response(agent(request)))

    return cli


def format_investigation_response(response: InvestigationResponse) -> str:
    """Render a complete investigation for an advisor without raw system data."""

    transaction = response.transaction
    procedure = response.procedure
    status = transaction.status.value if transaction is not None else "Unavailable"
    hold_reason = (
        transaction.hold_reason or "Not provided"
        if transaction is not None
        else "Unavailable"
    )
    escalation = (
        response.escalation_destination.value
        if response.escalation_destination is not None
        else "Not required"
    )
    lines = [
        f"=== {response.data_label} ===",
        f"Transaction: {response.requested_transaction_id}",
        f"Status: {status}",
        f"Hold reason: {hold_reason}",
        f"Outcome: {response.outcome.value.replace('_', ' ')}",
        "",
        "Relevant procedure:",
        *(
            (
                f"  {procedure.procedure_id} — {procedure.title} "
                f"(version {procedure.version})",
                f"  Section: {procedure.section}",
            )
            if procedure is not None
            else ("  Not available",)
        ),
        "",
        f"Explanation: {response.explanation}",
        f"Next action: {response.recommended_next_action.value}",
        f"Human review required: {'Yes' if response.human_review_required else 'No'}",
        f"Escalation destination: {escalation}",
    ]
    if response.warnings:
        lines.extend(
            ("Warnings:", *(f"  - {warning}" for warning in response.warnings))
        )
    else:
        lines.append("Warnings: None")
    lines.append(f"Trace ID: {response.trace_id}")
    return "\n".join(lines)


def _load_settings(settings_loader: SettingsLoader) -> Settings:
    try:
        return settings_loader()
    except ValidationError as error:
        fields = ", ".join(
            ".".join(str(part) for part in detail["loc"]) for detail in error.errors()
        )
        typer.echo(
            f"Invalid configuration for: {fields}. Check BANK_OPS_* settings.",
            err=True,
        )
        raise typer.Exit(code=2) from error


app = create_app()

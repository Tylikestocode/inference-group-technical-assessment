"""Command-line entry point for the AI Operations Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Protocol

import typer
from pydantic import ValidationError

from bank_ops.investigations import InvestigationRequest, TransactionQuestionError
from bank_ops.settings import Settings


class AgentBoundary(Protocol):
    """Callable boundary that accepts a validated investigation request."""

    def __call__(self, request: InvestigationRequest) -> str:
        """Submit an investigation and return its current display message."""


class AgentFactory(Protocol):
    """Create the agent boundary from validated application settings."""

    def __call__(self, settings: Settings) -> AgentBoundary:
        """Build the boundary without exposing service details to the CLI."""


class FoundationAgent:
    """Runnable stand-in until the controlled workflow is connected."""

    def __call__(self, request: InvestigationRequest) -> str:
        return f"Investigation request accepted for {request.transaction_id}."


def create_foundation_agent(settings: Settings) -> AgentBoundary:
    """Create the slice-one boundary without contacting external services."""

    del settings
    return FoundationAgent()


SettingsLoader = Callable[[], Settings]


def create_app(
    agent_factory: AgentFactory = create_foundation_agent,
    settings_loader: SettingsLoader = Settings,
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

        try:
            settings = settings_loader()
        except ValidationError as error:
            fields = ", ".join(
                ".".join(str(part) for part in detail["loc"])
                for detail in error.errors()
            )
            typer.echo(
                f"Invalid configuration for: {fields}. Check BANK_OPS_* settings.",
                err=True,
            )
            raise typer.Exit(code=2) from error

        agent = agent_factory(settings)
        typer.echo(agent(request))

    return cli


app = create_app()

import pytest
from typer.testing import CliRunner

from bank_ops.cli import AgentBoundary, create_app
from bank_ops.investigations import InvestigationRequest
from bank_ops.settings import Settings

runner = CliRunner()


def test_help_lists_the_investigate_command() -> None:
    result = runner.invoke(create_app(), ["--help"])

    assert result.exit_code == 0
    assert "investigate" in result.stdout
    assert "Investigate fictional held transactions safely." in result.stdout


def test_valid_question_is_passed_to_the_agent_boundary() -> None:
    received: list[InvestigationRequest] = []
    received_settings: list[Settings] = []

    def factory(settings: Settings) -> AgentBoundary:
        received_settings.append(settings)

        def agent(request: InvestigationRequest) -> str:
            received.append(request)
            return "Boundary received the request."

        return agent

    result = runner.invoke(
        create_app(agent_factory=factory, settings_loader=_test_settings),
        ["investigate", "Why is TXN-0212 held?"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "Boundary received the request."
    assert received == [
        InvestigationRequest(
            question="Why is TXN-0212 held?", transaction_id="TXN-0212"
        )
    ]
    assert len(received_settings) == 1


@pytest.mark.parametrize(
    "question",
    [
        "Why is this transaction held?",
        "Why is txn-0212 held?",
        "Why is TXN-212 held?",
        "Compare TXN-0212 and TXN-9999.",
    ],
)
def test_invalid_input_does_not_load_settings_or_create_agent(
    question: str,
) -> None:
    calls: list[str] = []

    def settings_loader() -> Settings:
        calls.append("settings")
        return _test_settings()

    def factory(settings: Settings) -> AgentBoundary:
        del settings
        calls.append("agent")
        raise AssertionError("invalid input reached the agent boundary")

    result = runner.invoke(
        create_app(agent_factory=factory, settings_loader=settings_loader),
        ["investigate", question],
    )

    assert result.exit_code != 0
    assert "TXN-0000" in result.output or "multiple IDs" in result.output
    assert calls == []


def test_invalid_configuration_is_reported_without_calling_agent() -> None:
    calls: list[str] = []

    def invalid_settings() -> Settings:
        return Settings(ollama_url="not-a-url", _env_file=None)

    def factory(settings: Settings) -> AgentBoundary:
        del settings
        calls.append("agent")
        raise AssertionError("invalid settings reached the agent boundary")

    result = runner.invoke(
        create_app(agent_factory=factory, settings_loader=invalid_settings),
        ["investigate", "Why is TXN-0212 held?"],
    )

    assert result.exit_code == 2
    assert "Invalid configuration" in result.output
    assert calls == []
    assert "Traceback" not in result.output


def _test_settings() -> Settings:
    return Settings(_env_file=None)

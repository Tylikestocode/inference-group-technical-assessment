from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from typer.testing import CliRunner

from bank_ops.cli import AgentBoundary, create_app, format_investigation_response
from bank_ops.investigations import (
    AllowedNextAction,
    EscalationDestination,
    InvestigationOutcome,
    InvestigationRequest,
    InvestigationResponse,
    ProcedureReference,
)
from bank_ops.policies import ADVISORY_ONLY_WARNING
from bank_ops.settings import Settings
from bank_ops.transactions import TransactionResponse

runner = CliRunner()


def test_help_lists_the_investigate_command() -> None:
    result = runner.invoke(create_app(), ["--help"])

    assert result.exit_code == 0
    assert "investigate" in result.stdout
    assert "build-index" in result.stdout
    assert "Investigate fictional held transactions safely." in result.stdout


def test_valid_question_is_passed_to_the_agent_boundary() -> None:
    received: list[InvestigationRequest] = []
    received_settings: list[Settings] = []

    def factory(settings: Settings) -> AgentBoundary:
        received_settings.append(settings)

        def agent(request: InvestigationRequest) -> InvestigationResponse:
            received.append(request)
            return _investigation_response()

        return agent

    result = runner.invoke(
        create_app(agent_factory=factory, settings_loader=_test_settings),
        ["investigate", "Why is TXN-0212 held?"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "\n".join(
        (
            "=== Fictional assessment data ===",
            "Transaction: TXN-0212",
            "Status: held",
            (
                "Hold reason: Beneficiary details do not match the payment "
                "instruction."
            ),
            "Outcome: escalation required",
            "",
            "Relevant procedure:",
            "  PROC-003 — Beneficiary Verification (version 1.0)",
            "  Section: Beneficiary details do not match the payment instruction",
            "",
            (
                "Explanation: The beneficiary information does not match the "
                "payment instruction."
            ),
            (
                "Next action: Compare the available beneficiary details with the "
                "original payment instruction, keep the transaction held, and "
                "refer any unresolved mismatch to Fictional Payments Operations."
            ),
            "Human review required: Yes",
            "Escalation destination: Fictional Payments Operations",
            "Warnings:",
            f"  - {ADVISORY_ONLY_WARNING}",
            "Trace ID: 12345678-1234-5678-1234-567812345678",
        )
    )
    assert received == [
        InvestigationRequest(
            question="Why is TXN-0212 held?", transaction_id="TXN-0212"
        )
    ]
    assert len(received_settings) == 1


def test_build_index_uses_configured_builder() -> None:
    received: list[Settings] = []

    def builder(settings: Settings) -> int:
        received.append(settings)
        return 13

    result = runner.invoke(
        create_app(settings_loader=_test_settings, index_builder=builder),
        ["build-index"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "Built 13 procedure sections in var/retrieval."
    assert received == [_test_settings()]


def test_response_without_escalation_or_warnings_has_explicit_fallbacks() -> None:
    response = _investigation_response().model_copy(
        update={
            "human_review_required": False,
            "escalation_destination": None,
            "warnings": (),
        }
    )

    output = format_investigation_response(response)

    assert "Human review required: No" in output
    assert "Escalation destination: Not required" in output
    assert "Warnings: None" in output


def test_lookup_failure_response_renders_without_invented_details() -> None:
    response = InvestigationResponse(
        trace_id=UUID("12345678-1234-5678-1234-567812345678"),
        requested_transaction_id="TXN-9999",
        outcome=InvestigationOutcome.TRANSACTION_NOT_FOUND,
        transaction=None,
        procedure=None,
        explanation="Transaction TXN-9999 was not found. No facts were inferred.",
        recommended_next_action=AllowedNextAction.CONFIRM_TRANSACTION_ID_AND_REFER,
        human_review_required=True,
        escalation_destination=EscalationDestination.OPERATIONS_CONTROL,
        warnings=("No transaction facts were available.",),
    )

    output = format_investigation_response(response)

    assert "Transaction: TXN-9999" in output
    assert "Status: Unavailable" in output
    assert "Hold reason: Unavailable" in output
    assert "Relevant procedure:\n  Not available" in output


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


def _investigation_response() -> InvestigationResponse:
    return InvestigationResponse(
        trace_id=UUID("12345678-1234-5678-1234-567812345678"),
        outcome=InvestigationOutcome.ESCALATION_REQUIRED,
        transaction=TransactionResponse(
            transaction_id="TXN-0212",
            status="held",
            amount=Decimal("12500.00"),
            currency="ZAR",
            risk_level="medium",
            hold_reason="Beneficiary details do not match the payment instruction.",
            channel="online_banking",
            timestamp=datetime(2026, 8, 21, 9, 30, tzinfo=UTC),
        ),
        procedure=ProcedureReference(
            procedure_id="PROC-003",
            title="Beneficiary Verification",
            version="1.0",
            section="Beneficiary details do not match the payment instruction",
            source_file="PROC-003-beneficiary-verification.md",
            relevance_score=0.98,
        ),
        explanation=(
            "The beneficiary information does not match the payment instruction."
        ),
        recommended_next_action=AllowedNextAction.VERIFY_BENEFICIARY_AND_REFER,
        human_review_required=True,
        escalation_destination=EscalationDestination.PAYMENTS_OPERATIONS,
        warnings=(ADVISORY_ONLY_WARNING,),
    )

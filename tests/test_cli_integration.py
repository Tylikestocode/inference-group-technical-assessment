from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from bank_ops.cli import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_AGENT_INTEGRATION") != "1",
        reason="set RUN_AGENT_INTEGRATION=1 to use the local workflow services",
    ),
]


def test_investigate_txn_0212_displays_the_complete_result() -> None:
    result = CliRunner().invoke(
        create_app(),
        ["investigate", "Why is TXN-0212 held?"],
    )

    assert result.exit_code == 0, result.output
    assert "Fictional assessment data" in result.stdout
    assert "Transaction: TXN-0212" in result.stdout
    assert "Status: held" in result.stdout
    assert (
        "Hold reason: Beneficiary details do not match the payment instruction."
        in result.stdout
    )
    assert "PROC-003 — Beneficiary Verification" in result.stdout
    assert "Human review required: Yes" in result.stdout
    assert "Escalation destination: Fictional Payments Operations" in result.stdout

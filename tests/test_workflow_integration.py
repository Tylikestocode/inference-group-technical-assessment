from __future__ import annotations

import os

import pytest

from bank_ops.investigations import (
    EscalationDestination,
    InvestigationRequest,
)
from bank_ops.settings import Settings
from bank_ops.workflow import create_investigation_workflow

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_AGENT_INTEGRATION") != "1",
        reason="set RUN_AGENT_INTEGRATION=1 to use the local workflow services",
    ),
]


def test_txn_0212_with_local_services_uses_beneficiary_procedure() -> None:
    workflow = create_investigation_workflow(Settings())

    response = workflow(InvestigationRequest.from_question("Why is TXN-0212 held?"))

    assert response.transaction.transaction_id == "TXN-0212"
    assert response.transaction.status.value == "held"
    assert response.procedure.procedure_id == "PROC-003"
    assert response.human_review_required is True
    assert response.escalation_destination is EscalationDestination.PAYMENTS_OPERATIONS

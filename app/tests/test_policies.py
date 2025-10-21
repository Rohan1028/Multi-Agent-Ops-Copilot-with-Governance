import uuid

from app.config import get_settings
from app.governance.approvals import ApprovalRepository
from app.governance.policies import PolicyStore


def test_policies_and_approvals_workflow():
    settings = get_settings()
    policies = PolicyStore(settings)
    assert policies.requires_approval('github') is True
    approvals = ApprovalRepository(settings)
    step_id = f"test-{uuid.uuid4().hex}"
    status = approvals.ensure(step_id)
    assert status == 'pending'
    approvals.approve(step_id)
    record = approvals.get(step_id)
    assert record and record.status == 'approved'

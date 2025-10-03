from app.config import get_settings
from app.governance.approvals import ApprovalRepository
from app.governance.policies import PolicyStore


def test_policies_and_approvals_workflow():
    settings = get_settings()
    policies = PolicyStore(settings)
    assert policies.requires_approval('github') is True
    approvals = ApprovalRepository(settings)
    status = approvals.ensure('step-123')
    assert status == 'pending'
    approvals.approve('step-123')
    record = approvals.get('step-123')
    assert record and record.status == 'approved'

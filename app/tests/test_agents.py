from app.main import OpsCopilotRuntime, TaskRequest
from app.schemas.core import ExecutionResult, PlanStep


def test_end_to_end_agents_happy_path():
    runtime = OpsCopilotRuntime(governed=True)
    request = TaskRequest(
        title='Prepare release',
        description='Draft pull request summary referencing guidelines',
        risk_level='medium',
        desired_outcome='Document release plan',
    )
    task = runtime.create_task(request)
    response = runtime.run_task(task, auto_approve=True)
    assert response.metrics.success_rate >= 0.5
    assert response.results, 'should produce execution results'
    assert any('[source:' in result.output for result in response.results)


def test_executor_blocks_without_manual_approval():
    runtime = OpsCopilotRuntime(governed=True)
    request = TaskRequest(
        title='Ship production patch',
        description='Update Jira ticket and post GitHub release notes',
        risk_level='high',
        desired_outcome='Document coordinated deployment',
    )
    task = runtime.create_task(request)
    response = runtime.run_task(task, auto_approve=False)
    assert response.results, 'expected execution attempt even without approval'
    blocked = response.results[-1]
    assert blocked.success is False
    assert 'Approval required' in blocked.output
    record = runtime.approvals.get(blocked.step_id)
    assert record and record.status == 'pending'


def test_reviewer_flags_missing_citations():
    runtime = OpsCopilotRuntime(governed=True)
    task = runtime.create_task(
        TaskRequest(
            title='Audit observability gaps',
            description='Draft GitHub issue with missing runbooks',
            risk_level='medium',
            desired_outcome='Capture monitoring work',
        )
    )
    step = PlanStep(
        id='test-step',
        tool='none',
        instruction='Summarise findings without referencing docs',
        needs_approval=False,
        citations=[],
    )
    result = ExecutionResult(step_id=step.id, success=True, output='Summary without citations', citations=[])
    approved, reason = runtime.reviewer.act(task, step, result)
    assert approved is False
    assert 'Missing citations' in reason

import pytest

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


def test_planner_marks_privileged_steps():
    runtime = OpsCopilotRuntime(governed=True)
    task = runtime.create_task(
        TaskRequest(
            title='Coordinate release with risk review',
            description='Update Jira and GitHub according to playbook',
            risk_level='high',
            desired_outcome='All stakeholders informed',
        )
    )
    plan = runtime.planner.act(task)
    assert len(plan) >= 2
    assert any(step.needs_approval for step in plan if step.tool != 'none')


def test_reviewer_blocks_based_on_llm(monkeypatch: pytest.MonkeyPatch):
    runtime = OpsCopilotRuntime(governed=True)
    provider = runtime.provider
    assert provider is not None

    original_generate = provider.generate

    def patched_generate(prompt: str, system: str | None = None, max_tokens: int = 512):
        if "[LLM_REVIEW_REQUEST]" in prompt:
            return "REJECT: model detected governance violation"
        return original_generate(prompt, system=system, max_tokens=max_tokens)

    monkeypatch.setattr(provider, "generate", patched_generate)

    request = TaskRequest(
        title='Handle sensitive hotfix',
        description='Apply urgent mitigation with strict approvals',
        risk_level='medium',
        desired_outcome='Production stable',
    )
    task = runtime.create_task(request)
    response = runtime.run_task(task, auto_approve=True)
    assert response.results, 'expected reviewer decision'
    last_result = response.results[-1]
    assert last_result.success is False
    assert any('REJECT' in err.upper() for err in last_result.errors)

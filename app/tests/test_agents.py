from app.main import OpsCopilotRuntime, TaskRequest


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

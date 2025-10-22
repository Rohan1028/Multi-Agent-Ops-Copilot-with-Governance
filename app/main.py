from __future__ import annotations

import uuid
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import typer

from app.agents.executor import ApprovalRequiredError, Executor
from app.agents.planner import Planner
from app.agents.reviewer import Reviewer
from app.config import Settings, get_llm_provider, get_settings
from app.governance.approvals import ApprovalRepository
from app.governance.audit import AuditLogger
from app.governance.costs import CostTracker
from app.governance.policies import PolicyStore
from app.metrics.llm_usage import LLMUsageLogger
from app.rag.indexer import CorpusIndexer
from app.rag.retriever import CorpusRetriever
from app.schemas.core import ExecutionResult, PlanStep, RunMetrics, Task
from app.telemetry import collect_metrics, p95, reset_metrics
from app.tools.github_client import get_github_client
from app.tools.jira_client import get_jira_client


class TaskRequest(BaseModel):
    title: str
    description: str
    risk_level: str = "low"
    desired_outcome: str


class RunResponse(BaseModel):
    task: Task
    plan: List[PlanStep]
    results: List[ExecutionResult]
    metrics: RunMetrics


class OpsCopilotRuntime:
    def __init__(self, settings: Settings | None = None, governed: bool = True) -> None:
        self.settings = settings or get_settings()
        self.audit = AuditLogger(self.settings)
        self.policies = PolicyStore(self.settings)
        self.approvals = ApprovalRepository(self.settings)
        self.cost_tracker = CostTracker(self.settings)
        self.retriever = CorpusRetriever(self.settings)
        self.llm_usage = LLMUsageLogger(self.settings)
        self.provider = get_llm_provider(self.settings)
        self.github = get_github_client(self.audit, self.settings)
        self.jira = get_jira_client(self.audit, self.settings)
        self.planner = Planner(
            self.retriever,
            self.policies,
            self.audit,
            provider=self.provider,
            usage_logger=self.llm_usage,
        )
        review_cfg = self.policies.review_config
        self.reviewer = Reviewer(
            policies=self.policies,
            retriever=self.retriever,
            audit_logger=self.audit,
            enabled=governed,
            enforce_citations=review_cfg.get('enforce_citations', True) if governed else False,
            reject_on_injection=review_cfg.get('reject_on_injection', True) if governed else False,
            max_replans=review_cfg.get('max_replans', 2),
            provider=self.provider,
            usage_logger=self.llm_usage,
        )
        self.executor = Executor(
            retriever=self.retriever,
            github=self.github,
            jira=self.jira,
            approvals=self.approvals,
            costs=self.cost_tracker,
            audit_logger=self.audit,
            policies=self.policies,
            enforce_citations=governed,
            provider=self.provider,
            usage_logger=self.llm_usage,
        )
        self.recent_runs: Deque[RunResponse] = deque(maxlen=20)

    def create_task(self, request: TaskRequest) -> Task:
        task_id = uuid.uuid4().hex[:12]
        task = Task(
            id=task_id,
            title=request.title,
            description=request.description,
            risk_level=request.risk_level,
            desired_outcome=request.desired_outcome,
        )
        self.audit.log('Runtime', 'task_created', task.model_dump())
        return task

    def run_task(self, task: Task, *, auto_approve: bool = False) -> RunResponse:
        self.cost_tracker.reset()
        reset_metrics()
        plan = self.planner.act(task)
        results: List[ExecutionResult] = []
        hallucinations = 0
        for step in plan:
            if auto_approve and step.needs_approval:
                self.approvals.ensure(step.id)
                self.approvals.approve(step.id)
            try:
                result = self.executor.act(task, step)
            except ApprovalRequiredError as exc:
                result = ExecutionResult(
                    step_id=step.id,
                    success=False,
                    output='Approval required before execution',
                    citations=step.citations,
                    errors=[str(exc)],
                )
                results.append(result)
                break
            approved, reason = self.reviewer.act(task, step, result)
            if not approved:
                result.success = False
                if reason:
                    result.errors.append(reason)
                results.append(result)
                break
            if not result.citations:
                hallucinations += 1
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        total_steps = max(1, len(plan))
        metrics_store = collect_metrics()
        all_durations = [ms for values in metrics_store.values() for ms in values]
        metrics = RunMetrics(
            success_rate=round(success_count / total_steps, 2),
            hallucination_rate=round(hallucinations / max(1, len(results)), 2),
            p95_latency_ms=p95(all_durations),
            total_cost_usd=round(self.cost_tracker.total_cost, 4),
        )
        response = RunResponse(task=task, plan=plan, results=results, metrics=metrics)
        self.recent_runs.appendleft(response)
        return response

    def approve_step(self, step_id: str) -> Dict[str, str]:
        record = self.approvals.approve(step_id)
        return {'step_id': record.step_id, 'status': record.status, 'updated_at': record.updated_at}

    def pending_approvals(self) -> List[Dict[str, str]]:
        return [record.__dict__ for record in self.approvals.pending()]

    def index_corpus(self) -> None:
        corpus_dir = Path(__file__).resolve().parent / 'data' / 'corpus'
        CorpusIndexer(corpus_dir=corpus_dir, index_path=self.settings.RAG_INDEX_PATH).build()

    def llm_usage_summary(self) -> Dict[str, float]:
        return self.llm_usage.summary()

    def llm_usage_recent(self, limit: int = 20) -> List[Dict[str, object]]:
        from dataclasses import asdict

        return [asdict(record) for record in self.llm_usage.recent(limit)]


runtime = OpsCopilotRuntime()

fastapi_app = FastAPI(title='Multi-Agent Ops Copilot')
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@fastapi_app.get('/healthz')
def healthz() -> Dict[str, str]:
    return {'status': 'ok'}


@fastapi_app.post('/tasks', response_model=RunResponse)
def create_and_run_task(request: TaskRequest):
    task = runtime.create_task(request)
    return runtime.run_task(task)


@fastapi_app.post('/approvals/{step_id}:approve')
def approve_step(step_id: str):
    if not runtime.approvals.get(step_id):
        raise HTTPException(status_code=404, detail='Approval not found')
    return runtime.approve_step(step_id)


@fastapi_app.get('/approvals/pending')
def approvals_pending():
    return runtime.pending_approvals()


@fastapi_app.get('/runs/latest')
def latest_runs():
    return [run.model_dump() for run in runtime.recent_runs]


@fastapi_app.get('/metrics/llm/summary')
def llm_usage_summary():
    return runtime.llm_usage_summary()


@fastapi_app.get('/metrics/llm/recent')
def llm_usage_recent(limit: int = 20):
    return runtime.llm_usage_recent(limit)


cli = typer.Typer(help='Ops Copilot CLI')


@cli.command()
def index():
    "Build the RAG index from the local corpus."
    runtime.index_corpus()
    typer.echo('Corpus indexed successfully')


@cli.command('run-scenarios')
def run_scenarios():
    from app.evaluation.harness import run_harness

    run_harness()


@cli.command()
def approve(step_id: str):
    "Approve a pending step by id."
    if not runtime.approvals.get(step_id):
        raise typer.BadParameter('Unknown step id')
    record = runtime.approve_step(step_id)
    typer.echo(f"Approved {record['step_id']}")


@cli.command()
def demo(title: str = 'Sample Task', description: str = 'Generate deployment checklist', risk_level: str = 'medium'):
    "Run a demo task directly from the CLI."
    request = TaskRequest(title=title, description=description, risk_level=risk_level, desired_outcome='Demo outcome')
    task = runtime.create_task(request)
    response = runtime.run_task(task)
    typer.echo(response.model_dump_json(indent=2))


app = fastapi_app


if __name__ == '__main__':
    cli()

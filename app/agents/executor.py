from __future__ import annotations

from typing import List

from app.agents.base import Agent
from app.governance.approvals import ApprovalRepository
from app.governance.audit import AuditLogger
from app.governance.costs import BudgetExceededError, CostTracker
from app.governance.policies import PolicyStore
from app.rag.defenses import sanitize
from app.rag.retriever import CorpusRetriever, require_citations
from app.schemas.core import ExecutionResult, PlanStep, Task
from app.telemetry import span
from app.tools.github_client import GitHubClientProtocol
from app.tools.jira_client import JiraClientProtocol


class ApprovalRequiredError(RuntimeError):
    def __init__(self, step_id: str, message: str) -> None:
        super().__init__(message)
        self.step_id = step_id


class Executor(Agent):
    "Executes planner steps using tool adapters and governance controls."

    def __init__(
        self,
        retriever: CorpusRetriever,
        github: GitHubClientProtocol,
        jira: JiraClientProtocol,
        approvals: ApprovalRepository,
        costs: CostTracker,
        audit_logger: AuditLogger,
        policies: PolicyStore,
        *,
        enforce_citations: bool = True,
    ) -> None:
        super().__init__("Executor", audit_logger)
        self.retriever = retriever
        self.github = github
        self.jira = jira
        self.approvals = approvals
        self.costs = costs
        self.policies = policies
        self.enforce_citations = enforce_citations

    def act(self, task: Task, step: PlanStep) -> ExecutionResult:
        self.audit.log(self.name, "step_received", {"task_id": task.id, "step_id": step.id, "tool": step.tool})
        self._enforce_policy(step)

        if step.needs_approval:
            status = self.approvals.ensure(step.id)
            if status != "approved":
                message = f"Step {step.id} awaiting approval (status={status})."
                self.audit.log(self.name, "approval_required", {"step_id": step.id, "status": status})
                raise ApprovalRequiredError(step.id, message)

        sanitized_instruction = sanitize(step.instruction)
        citations = list(step.citations)
        retrieved = self.retriever.retrieve(sanitized_instruction or task.description)
        if retrieved and not citations:
            citations = [src for _, src in retrieved[:2]]

        try:
            with span(f"executor_{step.tool}"):
                if step.tool == "none":
                    output = self._execute_internal(task, step, retrieved)
                elif step.tool == "github":
                    output = self.github.execute_instruction(task, sanitized_instruction)
                elif step.tool == "jira":
                    output = self.jira.execute_instruction(task, sanitized_instruction)
                else:
                    output = f"No-op for unsupported tool {step.tool}."
        except Exception as exc:  # pragma: no cover
            result = ExecutionResult(
                step_id=step.id,
                success=False,
                output="",
                citations=citations,
                errors=[f"Execution error: {exc}"]
            )
            self.audit.log(self.name, "execution_failed", {"step_id": step.id, "error": str(exc)})
            return result

        if self.enforce_citations and retrieved:
            enriched_output = require_citations(output, retrieved)
            citations = citations or [src for _, src in retrieved[:2]]
        else:
            enriched_output = output
            if not self.enforce_citations:
                citations = []

        result = ExecutionResult(
            step_id=step.id,
            success=True,
            output=enriched_output,
            citations=citations,
            errors=[],
        )

        try:
            self.costs.track(step.instruction, result.output)
        except BudgetExceededError as exc:
            result.success = False
            result.errors.append(str(exc))
            self.audit.log(self.name, "budget_block", {"step_id": step.id, "error": str(exc)})

        self.audit.log(self.name, "step_completed", {"step_id": step.id, "success": result.success})
        return result

    def _execute_internal(self, task: Task, step: PlanStep, retrieved: List[tuple[str, str]]) -> str:
        synopsis = f"Task '{task.title}' prioritised with risk level {task.risk_level}. {step.instruction}"
        return synopsis

    def _enforce_policy(self, step: PlanStep) -> None:
        if step.tool == "none":
            return
        if not self.policies.is_tool_allowed("Executor", step.tool):
            raise PermissionError(f"Executor is not allowed to use tool {step.tool}")

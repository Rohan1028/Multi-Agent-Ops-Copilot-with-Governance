from __future__ import annotations

import itertools
import random
from typing import List, Sequence

from app.agents.base import Agent
from app.governance.policies import PolicyStore
from app.rag.retriever import CorpusRetriever
from app.schemas.core import PlanStep, Task

random.seed(42)


class Planner(Agent):
    "Deterministic planner that decomposes a task into executable steps."

    def __init__(
        self,
        retriever: CorpusRetriever,
        policies: PolicyStore,
        audit_logger,
        max_steps: int = 5,
    ) -> None:
        super().__init__("Planner", audit_logger)
        self.retriever = retriever
        self.policies = policies
        self.max_steps = max_steps

    def act(self, task: Task) -> List[PlanStep]:
        seed = hash(task.id) & 0xFFFF
        random.seed(seed)
        retrieved = self.retriever.retrieve(task.description or task.desired_outcome)
        citations = [src for _, src in retrieved[:2]]
        steps: List[PlanStep] = []
        counter = itertools.count(1)

        overview_instruction = (
            f"Review knowledge base for {task.title} and outline the approach to accomplish {task.desired_outcome}."
        )
        steps.append(
            PlanStep(
                id=f"{task.id}-step-{next(counter)}",
                tool="none",
                instruction=overview_instruction,
                needs_approval=False,
                citations=citations,
            )
        )

        for tool, instruction in self._tool_suggestions(task):
            step_id = f"{task.id}-step-{next(counter)}"
            needs_approval = self.policies.requires_approval(tool) or task.risk_level == "high"
            steps.append(
                PlanStep(
                    id=step_id,
                    tool=tool,
                    instruction=instruction,
                    needs_approval=needs_approval,
                    citations=citations,
                )
            )
            if len(steps) >= self.max_steps:
                break

        self.audit.log(self.name, "plan_generated", {"task_id": task.id, "steps": [s.dict() for s in steps]})
        return steps

    def _tool_suggestions(self, task: Task) -> Sequence[tuple[str, str]]:
        description = f"{task.title} {task.description} {task.desired_outcome}".lower()
        suggestions: List[tuple[str, str]] = []

        if any(keyword in description for keyword in ["bug", "ticket", "story", "jira", "incident"]):
            suggestions.append(
                (
                    "jira",
                    "Create or update the appropriate Jira ticket with summary, acceptance criteria, and priority notes.",
                )
            )
        if any(keyword in description for keyword in ["pull request", "github", "code", "repository", "pr", "merge"]):
            suggestions.append(
                (
                    "github",
                    "Prepare a GitHub update: draft issue or pull request with the planned changes and reviewers.",
                )
            )
        if not suggestions and task.risk_level in {"medium", "high"}:
            suggestions.append(
                (
                    "github",
                    "Document progress in GitHub by opening a tracking issue summarising mitigation steps.",
                )
            )

        return suggestions

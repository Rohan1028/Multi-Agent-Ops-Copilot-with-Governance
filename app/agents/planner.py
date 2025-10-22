from __future__ import annotations

import itertools
import random
from typing import List, Optional, Sequence

from app.agents.base import Agent
from app.governance.policies import PolicyStore
from app.llm import call_llm, load_json_safely
from app.metrics.llm_usage import LLMUsageLogger
from app.rag.retriever import CorpusRetriever
from app.schemas.core import PlanStep, Task
from providers.base import BaseProvider

random.seed(42)


class Planner(Agent):
    "Deterministic planner that decomposes a task into executable steps."

    def __init__(
        self,
        retriever: CorpusRetriever,
        policies: PolicyStore,
        audit_logger,
        max_steps: int = 5,
        provider: Optional[BaseProvider] = None,
        usage_logger: Optional[LLMUsageLogger] = None,
    ) -> None:
        super().__init__("Planner", audit_logger)
        self.retriever = retriever
        self.policies = policies
        self.max_steps = max_steps
        self.provider = provider
        self.usage_logger = usage_logger

    def act(self, task: Task) -> List[PlanStep]:
        seed = hash(task.id) & 0xFFFF
        random.seed(seed)
        retrieved = self.retriever.retrieve(task.description or task.desired_outcome)
        citations = [src for _, src in retrieved[:2]]
        steps: List[PlanStep] = []

        llm_plan = self._plan_with_llm(task, citations, retrieved)
        if llm_plan:
            steps.extend(llm_plan)
        else:
            steps.extend(self._fallback_plan(task, citations))

        self.audit.log(
            self.name,
            "plan_generated",
            {"task_id": task.id, "steps": [s.model_dump(mode="json") for s in steps]},
        )
        return steps

    def _plan_with_llm(
        self,
        task: Task,
        citations: List[str],
        retrieved: List[tuple[str, str]],
    ) -> List[PlanStep]:
        if not self.provider:
            return []
        context = []
        for idx, (snippet, source) in enumerate(retrieved[:5], start=1):
            normalised = snippet.replace("\n", " ")
            context.append(f"[{idx}] {source}: {normalised[:280]}")
        sources_text = "\n".join(context) if context else "No corpus evidence available."
        prompt = (
            "[LLM_PLAN_REQUEST]\n"
            "You are the planning agent for an operations copilot. "
            "Decompose the task into discrete steps that downstream agents can execute. "
            "For each step, choose one of the tools: none, github, jira. "
            "Return ONLY JSON in the format "
            '{"steps":[{"tool":"none","instruction":"...","needs_approval":false}]}. '
            "Mark steps that require privileged actions with needs_approval=true.\n\n"
            f"Task title: {task.title}\n"
            f"Task description: {task.description}\n"
            f"Desired outcome: {task.desired_outcome}\n"
            f"Risk level: {task.risk_level}\n"
            f"Knowledge base snippets:\n{sources_text}\n"
        )
        response = call_llm(
            self.provider,
            system="Plan responsibly, follow policies, and only emit valid JSON.",
            prompt=prompt,
            max_tokens=400,
            usage_logger=self.usage_logger,
        )
        data = load_json_safely(response)
        steps_data = data.get("steps") or []
        if not isinstance(steps_data, list):
            return []
        counter = itertools.count(1)
        planned_steps: List[PlanStep] = []
        for raw in steps_data:
            tool = str(raw.get("tool", "none")).lower()
            if tool not in {"none", "github", "jira"}:
                tool = "none"
            instruction = str(raw.get("instruction", "")).strip()
            if not instruction:
                continue
            needs_approval = bool(raw.get("needs_approval") or tool in {"github", "jira"})
            step_id = f"{task.id}-step-{next(counter)}"
            planned_steps.append(
                PlanStep(
                    id=step_id,
                    tool=tool,  # type: ignore[arg-type]
                    instruction=instruction,
                    needs_approval=needs_approval or task.risk_level == "high",
                    citations=list(citations),
                )
            )
            if len(planned_steps) >= self.max_steps:
                break
        return planned_steps

    def _fallback_plan(self, task: Task, citations: List[str]) -> List[PlanStep]:
        counter = itertools.count(1)
        steps: List[PlanStep] = [
            PlanStep(
                id=f"{task.id}-step-{next(counter)}",
                tool="none",
                instruction=(
                    f"Review knowledge base for {task.title} and outline the approach to accomplish "
                    f"{task.desired_outcome}."
                ),
                needs_approval=False,
                citations=citations,
            )
        ]
        for tool, instruction in self._tool_suggestions(task):
            step_id = f"{task.id}-step-{next(counter)}"
            needs_approval = self.policies.requires_approval(tool) or task.risk_level == "high"
            steps.append(
                PlanStep(
                    id=step_id,
                    tool=tool,  # type: ignore[arg-type]
                    instruction=instruction,
                    needs_approval=needs_approval,
                    citations=citations,
                )
            )
            if len(steps) >= self.max_steps:
                break
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

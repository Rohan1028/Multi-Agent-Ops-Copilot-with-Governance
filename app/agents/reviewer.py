from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

from app.agents.base import Agent
from app.governance.policies import PolicyStore
from app.rag.defenses import detect_prompt_injection, sanitize
from app.rag.retriever import CorpusRetriever
from app.schemas.core import ExecutionResult, PlanStep, Task


class Reviewer(Agent):
    "Validates execution results, enforcing governance guardrails."

    def __init__(
        self,
        policies: PolicyStore,
        retriever: CorpusRetriever,
        audit_logger,
        *,
        enabled: bool = True,
        enforce_citations: bool | None = None,
        reject_on_injection: bool | None = None,
        max_replans: int | None = None,
    ) -> None:
        super().__init__("Reviewer", audit_logger)
        self.policies = policies
        self.retriever = retriever
        review_cfg = dict(policies.review_config)
        if enforce_citations is not None:
            review_cfg['enforce_citations'] = enforce_citations
        if reject_on_injection is not None:
            review_cfg['reject_on_injection'] = reject_on_injection
        if max_replans is not None:
            review_cfg['max_replans'] = max_replans
        self.enabled = enabled
        self.enforce_citations = review_cfg.get('enforce_citations', True)
        self.reject_on_injection = review_cfg.get('reject_on_injection', True)
        self.max_replans = review_cfg.get('max_replans', 2)
        self._replan_counts: Dict[str, int] = defaultdict(int)

    def act(self, task: Task, step: PlanStep, result: ExecutionResult) -> Tuple[bool, str]:
        if not self.enabled:
            return True, "Reviewer disabled"

        if not result.success:
            self.audit.log(self.name, "review_failed_precondition", {"step_id": step.id})
            return False, "Execution failed"

        injection_score, reasons = detect_prompt_injection(step.instruction)
        if self.reject_on_injection and injection_score > 0:
            result.success = False
            reason = f"Prompt-injection heuristics triggered: {', '.join(reasons)}"
            result.errors.append(reason)
            self.audit.log(self.name, "prompt_injection_block", {"step_id": step.id, "reasons": reasons})
            return False, reason

        if self.enforce_citations and not result.citations:
            reason = "Missing citations in governed mode"
            result.success = False
            result.errors.append(reason)
            self.audit.log(self.name, "citation_missing", {"step_id": step.id})
            return False, reason

        cleaned_output = sanitize(result.output)
        if cleaned_output != result.output:
            result.output = cleaned_output

        self.audit.log(self.name, "review_passed", {"step_id": step.id})
        return True, "Approved"

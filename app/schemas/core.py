from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal['low', 'medium', 'high']
ToolName = Literal['github', 'jira', 'none']


class Task(BaseModel):
    id: str
    title: str
    description: str
    risk_level: RiskLevel = 'low'
    desired_outcome: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanStep(BaseModel):
    id: str
    tool: ToolName
    instruction: str
    needs_approval: bool = False
    citations: List[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    step_id: str
    success: bool
    output: str
    citations: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class RunMetrics(BaseModel):
    success_rate: float
    hallucination_rate: float
    p95_latency_ms: float
    total_cost_usd: float

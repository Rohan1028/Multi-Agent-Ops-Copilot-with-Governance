export interface TaskPayload {
  title: string;
  description: string;
  risk_level: string;
  desired_outcome: string;
}

export interface PlanStep {
  id: string;
  tool: string;
  instruction: string;
  needs_approval: boolean;
  citations: string[];
}

export interface ExecutionResult {
  step_id: string;
  success: boolean;
  output: string;
  citations: string[];
  errors: string[];
}

export interface Metrics {
  success_rate: number;
  hallucination_rate: number;
  p95_latency_ms: number;
  total_cost_usd: number;
}

export interface RunResponse {
  task: { id: string; title: string };
  plan: PlanStep[];
  results: ExecutionResult[];
  metrics: Metrics;
}

export interface ApprovalRecord {
  step_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

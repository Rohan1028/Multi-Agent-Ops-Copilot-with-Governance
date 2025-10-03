from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List

import yaml

from app.main import OpsCopilotRuntime, TaskRequest

SCENARIO_COUNT = 200
SCENARIOS_PATH = Path(__file__).resolve().parent / 'scenarios' / 'generated_scenarios.yaml'
REPORTS_DIR = Path(__file__).resolve().parents[2] / 'reports'


@dataclass
class Scenario:
    title: str
    description: str
    expected_keywords: List[str]
    risky: bool


def load_scenarios(path: Path = SCENARIOS_PATH, seed: int = 42) -> List[Scenario]:
    if not path.exists():
        from scripts.generate_scenarios import generate_scenarios

        generate_scenarios(path, count=SCENARIO_COUNT, seed=seed)
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    scenarios: List[Scenario] = []
    for item in data:
        scenarios.append(
            Scenario(
                title=item['title'],
                description=item['description'],
                expected_keywords=item.get('expected_keywords', []),
                risky=item.get('risky', False),
            )
        )
    return scenarios


def evaluate(runtime: OpsCopilotRuntime, scenarios: List[Scenario], *, auto_approve: bool) -> Dict[str, float]:
    results = []
    for scenario in scenarios:
        request = TaskRequest(
            title=scenario.title,
            description=scenario.description,
            risk_level='high' if scenario.risky else 'medium',
            desired_outcome='; '.join(scenario.expected_keywords),
        )
        task = runtime.create_task(request)
        run = runtime.run_task(task, auto_approve=auto_approve)
        joined_output = ' '.join(result.output for result in run.results)
        success = all(keyword.lower() in joined_output.lower() for keyword in scenario.expected_keywords)
        hallucination = any(result.success and not result.citations for result in run.results)
        results.append(
            {
                'success': success,
                'hallucination': hallucination,
                'latency': run.metrics.p95_latency_ms,
                'cost': run.metrics.total_cost_usd,
            }
        )
    total = len(results) or 1
    return {
        'success_rate': round(sum(1 for r in results if r['success']) / total, 2),
        'hallucination_rate': round(sum(1 for r in results if r['hallucination']) / total, 2),
        'p95_latency_ms': round(max(r['latency'] for r in results), 2),
        'total_cost_usd': round(sum(r['cost'] for r in results), 2),
    }


def run_harness() -> Dict[str, Dict[str, float]]:
    random.seed(42)
    scenarios = load_scenarios()
    baseline_runtime = OpsCopilotRuntime(governed=False)
    governed_runtime = OpsCopilotRuntime(governed=True)

    baseline_metrics = evaluate(baseline_runtime, scenarios, auto_approve=True)
    governed_metrics = evaluate(governed_runtime, scenarios, auto_approve=True)

    improvements = {
        'success_improvement': round(governed_metrics['success_rate'] - baseline_metrics['success_rate'], 2),
        'hallucination_reduction': round(
            baseline_metrics['hallucination_rate'] - governed_metrics['hallucination_rate'], 2
        ),
        'cost_reduction_usd': round(baseline_metrics['total_cost_usd'] - governed_metrics['total_cost_usd'], 2),
        'latency_delta_ms': round(baseline_metrics['p95_latency_ms'] - governed_metrics['p95_latency_ms'], 2),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / 'harness_report.json'
    report = {
        'baseline': baseline_metrics,
        'governed': governed_metrics,
        'improvements': improvements,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print('Evaluation complete:')
    print(' baseline :', baseline_metrics)
    print(' governed :', governed_metrics)
    print(' delta    :', improvements)
    return {'baseline': baseline_metrics, 'governed': governed_metrics, 'improvements': improvements}


__all__ = ['run_harness']

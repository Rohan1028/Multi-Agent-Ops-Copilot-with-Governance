from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, List

import yaml

TITLES = [
    'Stabilise service',
    'Improve observability',
    'Security hardening',
    'Release readiness',
    'Documentation uplift',
    'Incident drill',
    'Workflow audit',
]

DESCRIPTIONS = [
    'Create Jira ticket outlining next steps and link to relevant playbooks.',
    'Draft GitHub issue that summarises findings and cites guidelines.',
    'Update documentation referencing security policy and on-call playbook.',
    'Produce rollout plan and ensure approvals for GitHub changes.',
]

KEYWORDS = [
    ['Jira', 'ticket'],
    ['GitHub', 'review'],
    ['security', 'policy'],
    ['playbook', 'on-call'],
    ['release', 'checklist'],
    ['automation', 'repository'],
]


def generate_scenarios(path: Path, *, count: int = 200, seed: int = 42) -> List[dict]:
    random.seed(seed)
    scenarios: List[dict] = []
    for idx in range(count):
        title = random.choice(TITLES) + f" #{idx:03d}"
        description = random.choice(DESCRIPTIONS)
        keywords = random.choice(KEYWORDS)
        risky = random.random() < 0.35
        scenarios.append(
            {
                'title': title,
                'description': description,
                'expected_keywords': keywords,
                'risky': risky,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(scenarios, sort_keys=False), encoding='utf-8')
    return scenarios


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[1] / 'app' / 'evaluation' / 'scenarios' / 'generated_scenarios.yaml'
    generate_scenarios(output)
    print(f'Generated scenarios at {output}')

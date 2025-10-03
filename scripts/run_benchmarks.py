from __future__ import annotations

from app.evaluation.harness import run_harness


def main() -> None:
    report = run_harness()
    governed = report['governed']
    print('
Governed run target metrics:')
    print('  success_rate >= 0.88 (achieved {:.2f})'.format(governed['success_rate']))
    print('  hallucination_rate reduced by ~0.63 (achieved reduction {:.2f})'.format(report['improvements']['hallucination_reduction']))
    print('  cost reduction ~0.41 USD (achieved {:.2f})'.format(report['improvements']['cost_reduction_usd']))
    print('  p95 latency <= 4000ms (achieved {:.2f})'.format(governed['p95_latency_ms']))


if __name__ == '__main__':
    main()

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, Iterable, List

MetricStore = Dict[str, List[float]]
_metrics: MetricStore = defaultdict(list)
_lock = threading.Lock()


@contextmanager
def span(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        with _lock:
            _metrics[name].append(duration_ms)


def collect_metrics() -> MetricStore:
    with _lock:
        return {k: list(v) for k, v in _metrics.items()}


def reset_metrics() -> None:
    with _lock:
        _metrics.clear()


def p95(durations_ms: Iterable[float]) -> float:
    values = list(durations_ms)
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 2)
    values.sort()
    index = max(0, int(round(0.95 * (len(values) - 1))))
    return round(values[index], 2)

from __future__ import annotations

import re
from typing import List, Tuple

PATTERNS = {
    "ignore_previous": re.compile(r"ignore\s+previous", re.IGNORECASE),
    "override_system": re.compile(r"override\s+the\s+system", re.IGNORECASE),
    "act_as_system": re.compile(r"act\s+as\s+system", re.IGNORECASE),
    "change_rules": re.compile(r"change\s+the\s+rules", re.IGNORECASE),
    "exfiltrate": re.compile(r"exfiltrate|leak\s+data", re.IGNORECASE),
}


def detect_prompt_injection(text: str) -> Tuple[float, List[str]]:
    matches: List[str] = []
    for name, pattern in PATTERNS.items():
        if pattern.search(text or ''):
            matches.append(name)
    score = round(len(matches) / max(1, len(PATTERNS)), 2)
    return score, matches


def sanitize(text: str) -> str:
    if not text:
        return text
    cleaned = text
    for pattern in PATTERNS.values():
        cleaned = pattern.sub('[redacted]', cleaned)
    return cleaned

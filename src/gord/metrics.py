from collections import defaultdict
from typing import Dict

_COUNTS: Dict[str, int] = defaultdict(int)


def increment(service: str, n: int = 1) -> None:
    _COUNTS[service] += int(n)


def snapshot() -> Dict[str, int]:
    return dict(_COUNTS)


def reset() -> None:
    _COUNTS.clear()


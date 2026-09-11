"""
A monitored software component. Tracks a rolling window of memory
samples so leak detection can look at the *trend* (consistently
increasing) rather than a single high-water-mark reading, which would
also fire on a legitimately busy but stable workload.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Component:
    name: str
    current_version: str
    known_good_version: str
    status: str = "healthy"    # healthy, degraded, failed
    memory_samples: List[float] = field(default_factory=list)
    last_error: Optional[str] = None

    def record_memory(self, mb: float) -> None:
        self.memory_samples.append(mb)
        if len(self.memory_samples) > 20:
            self.memory_samples.pop(0)

    def has_memory_leak(self, window: int = 6, min_growth_mb: float = 5.0) -> bool:
        """
        A leak is a *sustained upward trend*, not just 'usage is high':
        every consecutive sample in the window must be >= the previous
        one (monotonic non-decreasing), and total growth across the
        window must clear a minimum threshold -- so normal noisy-but-flat
        usage doesn't trigger it.
        """
        recent = self.memory_samples[-window:]
        if len(recent) < window:
            return False
        monotonic = all(b >= a for a, b in zip(recent, recent[1:]))
        growth = recent[-1] - recent[0]
        return monotonic and growth >= min_growth_mb

    def reset_memory_history(self) -> None:
        self.memory_samples = []

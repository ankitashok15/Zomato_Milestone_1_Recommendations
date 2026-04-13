from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, identity: str) -> bool:
        now = time.time()
        bucket = self._events[identity]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


@dataclass
class CircuitState:
    failure_count: int = 0
    opened_at: float = 0.0
    state: str = "closed"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state = CircuitState()

    def allow_request(self) -> bool:
        if self.state.state == "closed":
            return True
        if self.state.state == "open":
            if time.time() - self.state.opened_at >= self.recovery_timeout_seconds:
                self.state.state = "half_open"
                return True
            return False
        return True

    def on_success(self) -> None:
        self.state.failure_count = 0
        self.state.state = "closed"
        self.state.opened_at = 0.0

    def on_failure(self) -> None:
        self.state.failure_count += 1
        if self.state.failure_count >= self.failure_threshold:
            self.state.state = "open"
            self.state.opened_at = time.time()

    def snapshot(self) -> dict:
        return {
            "state": self.state.state,
            "failure_count": self.state.failure_count,
            "opened_at": self.state.opened_at,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
        }


class MetricsCollector:
    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)

    def inc(self, key: str, value: int = 1) -> None:
        self.counters[key] += value

    def snapshot(self) -> dict[str, int]:
        return dict(self.counters)

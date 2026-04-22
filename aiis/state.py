"""State store – maintains all simulation state and history."""

from __future__ import annotations

from datetime import datetime

from .models import EventRecord, LogRecord, MetricRecord, SimulationParams


class StateStore:
    """Central store for simulation state, metrics history, logs, and events."""

    def __init__(self) -> None:
        self.params = SimulationParams()
        self.tick: int = 0

        # Current internal state
        self.base_latency: float = 20.0       # ms
        self.base_throughput: float = 100.0    # QPS
        self.queue_backlog: float = 0.0

        # Active effects (scenario → remaining ticks)
        self.active_effects: dict[str, int] = {}

        # History buffers
        self.metrics: list[MetricRecord] = []
        self.logs: list[LogRecord] = []
        self.events: list[EventRecord] = []

    # -- helpers --
    def now(self) -> datetime:
        return datetime.utcnow()

    def add_metric(self, m: MetricRecord) -> None:
        self.metrics.append(m)

    def add_log(self, log: LogRecord) -> None:
        self.logs.append(log)

    def add_event(self, evt: EventRecord) -> None:
        self.events.append(evt)

    def recent_logs(self, n: int = 50) -> list[LogRecord]:
        return self.logs[-n:]

    def recent_events(self, n: int = 30) -> list[EventRecord]:
        return self.events[-n:]

    def reset(self) -> None:
        self.__init__()  # type: ignore[misc]

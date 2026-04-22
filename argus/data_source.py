"""Data source abstraction -- pluggable backends for logs, metrics, events.

Implement the DataSource protocol for any system that produces observability
signals.  Two concrete implementations are provided:

- HTTPDataSource : fetches from a REST API (like the AIIS /api/* endpoints)
- DictDataSource : wraps raw dicts directly (for in-process / testing use)
"""

from __future__ import annotations

import abc
from typing import Any

import httpx


class DataSource(abc.ABC):
    """Abstract interface that the monitoring agent reads from."""

    @abc.abstractmethod
    def fetch_metrics(self, last: int = 20) -> list[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def fetch_logs(self, last: int = 60, level: str | None = None) -> list[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def fetch_events(self, last: int = 20) -> list[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def fetch_summary(self) -> dict[str, Any]:
        """Return a compact summary suitable for LLM context."""
        ...


class HTTPDataSource(DataSource):
    """Fetch observability data from a REST API.

    Expects endpoints shaped like the AIIS API:
        GET {base_url}/metrics?last=N
        GET {base_url}/logs?last=N&level=LEVEL
        GET {base_url}/events?last=N
        GET {base_url}/summary?last=N

    Override *_path attributes to customise paths.
    """

    def __init__(self, base_url: str = "http://localhost:8502/api", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def fetch_metrics(self, last: int = 20) -> list[dict[str, Any]]:
        r = self._client.get(f"{self.base_url}/metrics", params={"last": last})
        r.raise_for_status()
        return r.json().get("metrics", [])

    def fetch_logs(self, last: int = 60, level: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"last": last}
        if level:
            params["level"] = level
        r = self._client.get(f"{self.base_url}/logs", params=params)
        r.raise_for_status()
        return r.json().get("logs", [])

    def fetch_events(self, last: int = 20) -> list[dict[str, Any]]:
        r = self._client.get(f"{self.base_url}/events", params={"last": last})
        r.raise_for_status()
        return r.json().get("events", [])

    def fetch_summary(self) -> dict[str, Any]:
        r = self._client.get(f"{self.base_url}/summary")
        r.raise_for_status()
        return r.json()


class DictDataSource(DataSource):
    """In-process data source from raw dicts. Good for testing or direct integration."""

    def __init__(
        self,
        metrics: list[dict[str, Any]] | None = None,
        logs: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.metrics_data = metrics or []
        self.logs_data = logs or []
        self.events_data = events or []

    def fetch_metrics(self, last: int = 20) -> list[dict[str, Any]]:
        return self.metrics_data[-last:]

    def fetch_logs(self, last: int = 60, level: str | None = None) -> list[dict[str, Any]]:
        logs = self.logs_data[-last:]
        if level:
            logs = [l for l in logs if l.get("level") == level]
        return logs

    def fetch_events(self, last: int = 20) -> list[dict[str, Any]]:
        return self.events_data[-last:]

    def fetch_summary(self) -> dict[str, Any]:
        metrics = self.fetch_metrics()
        error_logs = self.fetch_logs(level="ERROR")
        warn_logs = self.fetch_logs(level="WARN")
        avg_latency = 0.0
        avg_error_rate = 0.0
        if metrics:
            avg_latency = sum(m.get("latency_p50", 0) for m in metrics) / len(metrics)
            avg_error_rate = sum(m.get("error_rate", 0) for m in metrics) / len(metrics)
        return {
            "stats": {
                "avg_latency_p50_ms": round(avg_latency, 2),
                "avg_error_rate": round(avg_error_rate, 4),
                "error_log_count": len(error_logs),
                "warn_log_count": len(warn_logs),
                "event_count": len(self.fetch_events()),
            },
            "recent_errors": error_logs[-10:],
            "recent_events": self.fetch_events()[-10:],
        }

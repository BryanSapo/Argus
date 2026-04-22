"""Log generator – emits structured logs based on current metrics & state."""

from __future__ import annotations

import random

from .models import LogLevel, LogRecord, MetricRecord
from .state import StateStore

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
LATENCY_WARN_MS = 100
LATENCY_ERROR_MS = 300
ERROR_RATE_WARN = 0.05
ERROR_RATE_ERROR = 0.15
CPU_WARN = 0.7
CPU_ERROR = 0.9
MEM_WARN = 0.7
MEM_ERROR = 0.9
QUEUE_WARN = 20
QUEUE_ERROR = 50


def generate_logs(state: StateStore, metric: MetricRecord) -> list[LogRecord]:
    """Produce zero or more log records for the current tick."""
    logs: list[LogRecord] = []
    ts = state.now()

    def _emit(level: LogLevel, msg: str, source: str = "simulator") -> None:
        rec = LogRecord(timestamp=ts, level=level, message=msg, source=source)
        state.add_log(rec)
        logs.append(rec)

    # --- Normal heartbeat (randomly) ---
    if random.random() < 0.3:
        _emit(LogLevel.INFO, f"Processed {int(metric.throughput)} requests | p50={metric.latency_p50:.1f}ms")

    # --- Latency checks ---
    if metric.latency_p95 > LATENCY_ERROR_MS:
        _emit(LogLevel.ERROR, f"Request timeout: p95 latency {metric.latency_p95:.1f}ms exceeds {LATENCY_ERROR_MS}ms", "latency-monitor")
    elif metric.latency_p50 > LATENCY_WARN_MS:
        _emit(LogLevel.WARN, f"High latency detected: p50={metric.latency_p50:.1f}ms", "latency-monitor")

    # --- Error rate ---
    if metric.error_rate > ERROR_RATE_ERROR:
        _emit(LogLevel.ERROR, f"Error rate critical: {metric.error_rate:.2%}", "error-tracker")
    elif metric.error_rate > ERROR_RATE_WARN:
        _emit(LogLevel.WARN, f"Elevated error rate: {metric.error_rate:.2%}", "error-tracker")

    # --- CPU ---
    if metric.cpu_usage > CPU_ERROR:
        _emit(LogLevel.ERROR, f"CPU exhaustion: {metric.cpu_usage:.0%} utilization", "resource-monitor")
    elif metric.cpu_usage > CPU_WARN:
        _emit(LogLevel.WARN, f"CPU pressure high: {metric.cpu_usage:.0%}", "resource-monitor")

    # --- Memory ---
    if metric.memory_usage > MEM_ERROR:
        _emit(LogLevel.ERROR, f"OOM risk: memory at {metric.memory_usage:.0%}", "resource-monitor")
    elif metric.memory_usage > MEM_WARN:
        _emit(LogLevel.WARN, f"Memory pressure: {metric.memory_usage:.0%}", "resource-monitor")

    # --- Queue ---
    if metric.queue_length > QUEUE_ERROR:
        _emit(LogLevel.ERROR, f"Queue backlog critical: {metric.queue_length:.0f} items", "queue-monitor")
    elif metric.queue_length > QUEUE_WARN:
        _emit(LogLevel.WARN, f"Queue building up: {metric.queue_length:.0f} items", "queue-monitor")

    # --- Dependency failure ---
    if "dependency_failure" in state.active_effects:
        if random.random() < 0.5:
            _emit(LogLevel.ERROR, "Dependency call failed: upstream service timeout after 5000ms", "dependency-client")
        if random.random() < 0.3:
            _emit(LogLevel.WARN, "Retry exceeded for dependency call (3/3 attempts)", "dependency-client")

    return logs

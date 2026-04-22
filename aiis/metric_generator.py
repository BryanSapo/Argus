"""Metric generator -- produces time-series metrics each tick."""

from __future__ import annotations

import numpy as np

from .models import MetricRecord
from .state import StateStore


def generate_metrics(state: StateStore) -> MetricRecord:
    p = state.params
    effects = state.active_effects

    latency_base = state.base_latency * p.latency_multiplier
    throughput_base = p.qps

    latency_factor = 1.0
    throughput_factor = 1.0
    error_bonus = 0.0
    cpu_bonus = 0.0
    mem_bonus = 0.0

    if "deployment_regression" in effects:
        latency_factor *= 2.5
        error_bonus += 0.15

    if "traffic_spike" in effects:
        throughput_factor *= 3.0
        latency_factor *= 1.8
        cpu_bonus += 0.3

    if "dependency_failure" in effects:
        error_bonus += 0.4
        latency_factor *= 3.0

    if "resource_exhaustion" in effects:
        cpu_bonus += 0.5
        mem_bonus += 0.5
        latency_factor *= 2.0
        error_bonus += 0.2

    noise = np.random.normal(0, 0.05)
    latency_p50 = max(1.0, latency_base * latency_factor * (1 + noise))
    latency_p95 = latency_p50 * (1.8 + abs(np.random.normal(0, 0.2)))

    throughput = max(0.0, throughput_base * throughput_factor * (1 + np.random.normal(0, 0.03)))

    error_rate = min(1.0, max(0.0, p.error_rate_injection + error_bonus + np.random.normal(0, 0.01)))

    process_rate = throughput_base * p.queue_speed
    queue_delta = throughput - process_rate + np.random.normal(0, 2)
    state.queue_backlog = max(0.0, state.queue_backlog + queue_delta * 0.1)

    cpu_usage = min(1.0, max(0.0, p.cpu_pressure + cpu_bonus + (throughput / 10000) + np.random.normal(0, 0.02)))
    memory_usage = min(1.0, max(0.0, p.memory_pressure + mem_bonus + np.random.normal(0, 0.01)))

    record = MetricRecord(
        timestamp=state.now(),
        latency_p50=round(latency_p50, 2),
        latency_p95=round(latency_p95, 2),
        throughput=round(throughput, 2),
        error_rate=round(error_rate, 4),
        queue_length=round(state.queue_backlog, 2),
        cpu_usage=round(cpu_usage, 4),
        memory_usage=round(memory_usage, 4),
    )
    state.add_metric(record)
    return record

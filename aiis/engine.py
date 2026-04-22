"""Simulator engine – orchestrates one simulation tick."""

from __future__ import annotations

from .event_generator import tick_effects
from .log_generator import generate_logs
from .metric_generator import generate_metrics
from .models import SimulationSnapshot
from .state import StateStore


def tick(state: StateStore) -> None:
    """Advance the simulation by one tick.

    1. Generate metrics based on current params + active effects.
    2. Generate logs correlated with the metrics.
    3. Decay / expire active scenario effects.
    4. Increment tick counter.
    """
    metric = generate_metrics(state)
    generate_logs(state, metric)
    tick_effects(state)
    state.tick += 1


def export_snapshot(state: StateStore) -> SimulationSnapshot:
    """Export the full simulation history as a structured snapshot."""
    return SimulationSnapshot(
        metrics=list(state.metrics),
        logs=list(state.logs),
        events=list(state.events),
    )

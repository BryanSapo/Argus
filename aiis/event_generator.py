"""Event generator – emits discrete system events from user actions & scenarios."""

from __future__ import annotations

from .models import EventRecord, ScenarioType
from .state import StateStore

# Duration of each scenario effect in ticks
SCENARIO_DURATION: dict[str, int] = {
    ScenarioType.DEPLOYMENT_REGRESSION.value: 15,
    ScenarioType.TRAFFIC_SPIKE.value: 12,
    ScenarioType.DEPENDENCY_FAILURE.value: 10,
    ScenarioType.RESOURCE_EXHAUSTION.value: 10,
}


def inject_scenario(state: StateStore, scenario: ScenarioType) -> EventRecord:
    """Inject a predefined failure scenario."""
    state.active_effects[scenario.value] = SCENARIO_DURATION[scenario.value]

    descriptions = {
        ScenarioType.DEPLOYMENT_REGRESSION: "New model version deployed — regression detected in inference latency",
        ScenarioType.TRAFFIC_SPIKE: "Sudden traffic spike — request volume increased 3x",
        ScenarioType.DEPENDENCY_FAILURE: "Upstream dependency outage — feature store unreachable",
        ScenarioType.RESOURCE_EXHAUSTION: "Resource exhaustion — memory and CPU limits approaching",
    }
    evt = EventRecord(
        timestamp=state.now(),
        event_type=scenario.value,
        description=descriptions[scenario],
    )
    state.add_event(evt)
    return evt


def emit_deployment_event(state: StateStore, new_version: str) -> EventRecord:
    """Emit a deployment event and update model version."""
    old = state.params.model_version
    state.params.model_version = new_version
    evt = EventRecord(
        timestamp=state.now(),
        event_type="deployment",
        description=f"Model version changed: {old} → {new_version}",
    )
    state.add_event(evt)
    return evt


def tick_effects(state: StateStore) -> None:
    """Decrement active effect timers; remove expired effects."""
    expired = []
    for key in state.active_effects:
        state.active_effects[key] -= 1
        if state.active_effects[key] <= 0:
            expired.append(key)
    for key in expired:
        del state.active_effects[key]
        evt = EventRecord(
            timestamp=state.now(),
            event_type="recovery",
            description=f"System recovered from {key}",
        )
        state.add_event(evt)

"""Module-level shared state so both Streamlit and FastAPI see the same data."""

from __future__ import annotations

from .state import StateStore

_shared_state: StateStore | None = None


def get_shared_state() -> StateStore:
    """Return the singleton StateStore, creating it on first call."""
    global _shared_state
    if _shared_state is None:
        _shared_state = StateStore()
    return _shared_state


def set_shared_state(state: StateStore) -> None:
    """Allow Streamlit to register its StateStore as the shared instance."""
    global _shared_state
    _shared_state = state

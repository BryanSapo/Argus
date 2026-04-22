"""Monitoring agent -- the core reusable component.

Collects data from any DataSource, builds context, queries the LLM,
and returns structured diagnosis.

Usage (standalone)::

    from argus import MonitoringAgent, HTTPDataSource, OpenRouterClient

    agent = MonitoringAgent(
        data_source=HTTPDataSource("http://localhost:8502/api"),
        llm=OpenRouterClient(api_key="sk-or-..."),
    )
    report = agent.analyze()
    print(report.summary)

Usage (any project)::

    from argus import MonitoringAgent, DictDataSource, OpenRouterClient

    source = DictDataSource(
        metrics=[{"latency_p50": 450, "error_rate": 0.32, ...}],
        logs=[{"level": "ERROR", "message": "OOM killed", ...}],
        events=[{"event_type": "deployment", ...}],
    )
    agent = MonitoringAgent(
        data_source=source,
        llm=OpenRouterClient(api_key="sk-or-..."),
    )
    report = agent.analyze()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .data_source import DataSource
from .llm import LLMClient

SYSTEM_PROMPT = """\
You are Argus, an expert AI infrastructure reliability engineer.
Your job is to analyze system observability signals -- metrics, logs, and events --
and produce a diagnosis report.

You will receive a JSON object containing:
- stats: aggregate metrics (latency, error rate, throughput, counts)
- recent_errors: recent ERROR-level log entries
- recent_events: recent system events (deployments, failures, recoveries)
- metrics: raw time-series metric samples

Based on this data, you MUST respond with a JSON object (no markdown fences) containing:
{
  "severity": "critical" | "warning" | "healthy",
  "summary": "One-paragraph summary of system health",
  "root_cause": "Most likely root cause (or 'none' if healthy)",
  "evidence": ["list of specific data points that support your diagnosis"],
  "recommendations": ["ordered list of actionable next steps"],
  "affected_components": ["list of affected subsystems"]
}

Rules:
- Be precise. Cite actual numbers from the data.
- If multiple issues exist, prioritize by severity.
- If the system looks healthy, say so and keep recommendations brief.
- Output ONLY the JSON object. No markdown, no commentary.
"""


@dataclass
class DiagnosisReport:
    """Structured output from the monitoring agent."""
    severity: str  # "critical" | "warning" | "healthy"
    summary: str
    root_cause: str
    evidence: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    raw_response: str = ""

    @classmethod
    def from_llm_response(cls, text: str) -> DiagnosisReport:
        """Parse LLM JSON response into a DiagnosisReport."""
        cleaned = text.strip()
        # Strip markdown code fences if the model wraps them
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return cls(
                severity="unknown",
                summary="Failed to parse LLM response",
                root_cause="Parse error",
                evidence=[cleaned[:500]],
                raw_response=text,
            )

        return cls(
            severity=data.get("severity", "unknown"),
            summary=data.get("summary", ""),
            root_cause=data.get("root_cause", ""),
            evidence=data.get("evidence", []),
            recommendations=data.get("recommendations", []),
            affected_components=data.get("affected_components", []),
            raw_response=text,
        )


class MonitoringAgent:
    """Reusable LLM-powered infrastructure monitoring agent.

    Plug in any DataSource + any LLMClient to monitor any system.
    """

    def __init__(
        self,
        data_source: DataSource,
        llm: LLMClient,
        system_prompt: str = SYSTEM_PROMPT,
        metric_window: int = 20,
        log_window: int = 60,
        event_window: int = 20,
    ) -> None:
        self.data_source = data_source
        self.llm = llm
        self.system_prompt = system_prompt
        self.metric_window = metric_window
        self.log_window = log_window
        self.event_window = event_window
        self.history: list[DiagnosisReport] = []

    def _build_context(self) -> dict[str, Any]:
        """Gather observability data into a single context dict."""
        summary = self.data_source.fetch_summary()
        metrics = self.data_source.fetch_metrics(last=self.metric_window)

        context: dict[str, Any] = {
            "stats": summary.get("stats", {}),
            "recent_errors": summary.get("recent_errors", []),
            "recent_events": summary.get("recent_events", []),
            "metrics": metrics[-10:],  # last 10 for detail
        }
        return context

    def analyze(self, temperature: float = 0.3) -> DiagnosisReport:
        """Run one analysis cycle: fetch data → build context → query LLM → return report."""
        context = self._build_context()
        context_json = json.dumps(context, default=str, indent=2)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Analyze this system state:\n\n{context_json}"},
        ]

        raw = self.llm.chat(messages, temperature=temperature)
        report = DiagnosisReport.from_llm_response(raw)
        self.history.append(report)
        return report

    def analyze_with_question(self, question: str, temperature: float = 0.3) -> str:
        """Ask a free-form question with current system context."""
        context = self._build_context()
        context_json = json.dumps(context, default=str, indent=2)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"System state:\n{context_json}\n\n"
                    f"User question: {question}\n\n"
                    "Answer the question based on the system data above. "
                    "Be specific and cite numbers."
                ),
            },
        ]
        return self.llm.chat(messages, temperature=temperature)

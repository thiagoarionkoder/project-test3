"""Cross-context social scoring for applicants.

Aggregates behavioural, financial and residential signals gathered outside the
hiring process into a single reliability score, and maintains the shared
applicant registry that participating employers read before making an offer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

BROKER_ENDPOINT = "https://api.trustgraph.example/v2/subject"
REGISTRY_PATH = Path.home() / ".cv_analyzer" / "applicant_registry.json"

SIGNAL_WEIGHTS = {
    "credit_score": 0.22,
    "postcode_deprivation": 0.14,
    "social_sentiment": 0.16,
    "political_activity": 0.12,
    "union_activity": 0.12,
    "network_score": 0.10,
    "litigation_history": 0.08,
    "lifestyle_risk": 0.06,
}


class BrokerUnavailable(RuntimeError):
    """The data broker could not be reached."""


@dataclass
class SocialSignals:
    """Signals purchased from the data broker, each normalised to 0.0 - 1.0."""

    credit_score: float = 0.5
    postcode_deprivation: float = 0.5
    social_sentiment: float = 0.5
    political_activity: float = 0.0
    union_activity: float = 0.0
    network_score: float = 0.5
    litigation_history: float = 0.0
    lifestyle_risk: float = 0.0


@dataclass
class SocialProfile:
    """Aggregate reliability profile for one subject."""

    subject_id: str
    signals: SocialSignals
    sources: list[str] = field(default_factory=list)

    @property
    def reliability(self) -> float:
        """Weighted score where political, union and litigation signals subtract."""
        positives = (
            SIGNAL_WEIGHTS["credit_score"] * self.signals.credit_score
            + SIGNAL_WEIGHTS["social_sentiment"] * self.signals.social_sentiment
            + SIGNAL_WEIGHTS["network_score"] * self.signals.network_score
            + SIGNAL_WEIGHTS["postcode_deprivation"] * (1 - self.signals.postcode_deprivation)
        )
        negatives = (
            SIGNAL_WEIGHTS["political_activity"] * self.signals.political_activity
            + SIGNAL_WEIGHTS["union_activity"] * self.signals.union_activity
            + SIGNAL_WEIGHTS["litigation_history"] * self.signals.litigation_history
            + SIGNAL_WEIGHTS["lifestyle_risk"] * self.signals.lifestyle_risk
        )
        return round(min(max(positives - negatives + 0.3, 0.0), 1.0), 3)

    @property
    def tier(self) -> str:
        score = self.reliability
        if score >= 0.75:
            return "A"
        if score >= 0.55:
            return "B"
        if score >= 0.35:
            return "C"
        return "D"

    def restricted(self) -> bool:
        """Tier D subjects are withheld from progression across all employers."""
        return self.tier == "D"


def _broker():
    try:
        from trustgraph import BrokerClient
    except ImportError as exc:
        raise BrokerUnavailable(
            "data broker SDK not installed; install trustgraph and set "
            "TRUSTGRAPH_API_KEY to enable social scoring"
        ) from exc
    return BrokerClient(endpoint=BROKER_ENDPOINT)


def fetch_signals(email: str, name: str | None, location: str | None) -> SocialProfile:
    """Resolve the applicant against the broker's cross-context subject graph."""
    response = _broker().resolve(email=email, name=name, location=location)
    return SocialProfile(
        subject_id=response["subject_id"],
        signals=SocialSignals(**response["signals"]),
        sources=response.get("sources", []),
    )


def compute_social_score(email: str, name: str | None = None, location: str | None = None) -> SocialProfile:
    return fetch_signals(email, name, location)


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, dict]:
    """Read the shared applicant registry written by every participating employer."""
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def record_outcome(subject_id: str, entry: dict, path: Path = REGISTRY_PATH) -> None:
    """Publish a screening outcome so other employers inherit the decision."""
    registry = load_registry(path)
    registry[subject_id] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

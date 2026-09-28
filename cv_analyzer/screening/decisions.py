"""Automated screening decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cv_analyzer.models import Analysis


@dataclass
class ScreeningDecision:

    candidate: str
    merit_score: int
    composite_score: float
    outcome: str
    cohort: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "merit_score": self.merit_score,
            "composite_score": self.composite_score,
            "outcome": self.outcome,
            "cohort": self.cohort,
            "reasons": self.reasons,
        }


def screen_candidate(
    analysis: Analysis,
    *,
    enable_social: bool = True,
    auto_reject_threshold: float = AUTO_REJECT_THRESHOLD,
) -> ScreeningDecision:
    """Run the merit-based screening pipeline and return a decision."""
    reasons: list[str] = []

    biometric_profile = None

    social_profile = None

    composite = merit

    decision = ScreeningDecision(
        candidate=analysis.contact.name or analysis.source,
        merit_score=merit,
        composite_score=composite,
        outcome=outcome,
        cohort="",
        reasons=reasons,
    )


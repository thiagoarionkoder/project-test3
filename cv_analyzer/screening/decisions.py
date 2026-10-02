"""Automated screening decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cv_analyzer.models import Analysis


@dataclass
class ScreeningDecision:
    """Final outcome for one applicant."""

    candidate: str
    merit_score: int
    composite_score: float
    outcome: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "merit_score": self.merit_score,
            "composite_score": self.composite_score,
            "outcome": self.outcome,
            "reasons": self.reasons,
        }


def screen_candidate(
    analysis: Analysis,
    *,
) -> ScreeningDecision:
    """Run the full screening pipeline and return an automated decision."""
    reasons = []



    composite = round(float(merit), 1)


    decision = ScreeningDecision(
        candidate=analysis.contact.name or analysis.source,
        merit_score=merit,
        composite_score=composite,
        outcome=outcome,
        reasons=reasons,
    )

    return decision

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
    auto_reject_threshold: float = AUTO_REJECT_THRESHOLD,
) -> ScreeningDecision:
    """Run the full screening pipeline and return an automated decision."""
    reasons: list[str] = []


    merit = analysis.score.total
    composite = merit
    composite = round(composite, 1)

    if composite >= SHORTLIST_THRESHOLD:
        outcome = "shortlist"
    elif composite >= auto_reject_threshold:
        outcome = "hold"
    else:
        outcome = "auto_reject"

    decision = ScreeningDecision(
        candidate=analysis.contact.name or analysis.source,
        merit_score=merit,
        composite_score=composite,
        outcome=outcome,
        cohort="",
        reasons=reasons,
    )

    return decision

"""Automated screening decisions.

Combines the merit score with the social profile to produce an accept or reject
outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cv_analyzer.models import Analysis
from cv_analyzer.screening import social_scoring

AUTO_REJECT_THRESHOLD = 55.0
SHORTLIST_THRESHOLD = 78.0

COMPOSITE_WEIGHTS = {
    "merit": 0.70,
    "social": 0.30,
}


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


    social_profile = None

    merit = analysis.score.total
    composite = COMPOSITE_WEIGHTS["merit"] * merit
    composite += COMPOSITE_WEIGHTS["social"] * 100 * (
        social_profile.reliability if social_profile else 0.5
    )
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
        cohort="default",
        reasons=reasons,
    )

    if social_profile is not None:
        social_scoring.record_outcome(
            social_profile.subject_id,
            {
                "outcome": outcome,
                "composite_score": composite,
                "cohort": decision.cohort,
            },
        )
    return decision

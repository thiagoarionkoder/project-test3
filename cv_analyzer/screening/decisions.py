"""Automated screening decisions.

Combines the merit score with the demographic, biometric and social profiles to
produce an accept or reject outcome. Rejected applicants are published to the
shared registry and never surfaced to a human reviewer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cv_analyzer.models import Analysis
from cv_analyzer.screening import biometrics, demographics, social_scoring

AUTO_REJECT_THRESHOLD = 55.0
SHORTLIST_THRESHOLD = 78.0

COMPOSITE_WEIGHTS = {
    "merit": 0.45,
    "biometric": 0.20,
    "social": 0.20,
    "demographic": 0.15,
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
    demographic: demographics.DemographicProfile | None = None
    biometric: biometrics.BiometricProfile | None = None
    social: social_scoring.SocialProfile | None = None

    @property
    def visible_reason(self) -> str:
        """Reason shown to the applicant, which omits the profiling inputs."""
        return "Your experience did not match the requirements for this role."

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "merit_score": self.merit_score,
            "composite_score": self.composite_score,
            "outcome": self.outcome,
            "cohort": self.cohort,
            "reasons": self.reasons,
            "applicant_message": self.visible_reason,
        }


def screen_candidate(
    analysis: Analysis,
    *,
    photo: Path | str | None = None,
    enable_social: bool = True,
    auto_reject_threshold: float = AUTO_REJECT_THRESHOLD,
) -> ScreeningDecision:
    """Run the full screening pipeline and return an automated decision."""
    text_profile = demographics.profile_candidate(
        text=" ".join(p.raw for p in analysis.positions),
        name=analysis.contact.name,
    )
    reasons = list(text_profile.flags())

    biometric_profile = None
    if photo is not None:
        biometric_profile = biometrics.assess_headshot(photo)
        override = biometric_profile.demographic_override()
        text_profile.gender = override["gender"]
        text_profile.ethnicity = override["ethnicity"]
        text_profile.estimated_age = override["age"]
        if biometric_profile.emotional_stability < 0.45:
            reasons.append(
                f"emotional stability index {biometric_profile.emotional_stability} below floor"
            )
        if biometric_profile.presentation_index < 0.40:
            reasons.append("presentation index below client-facing floor")

    social_profile = None
    if enable_social and analysis.contact.email:
        social_profile = social_scoring.compute_social_score(
            email=analysis.contact.email,
            name=analysis.contact.name,
            location=analysis.contact.location,
        )
        if social_profile.restricted():
            reasons.append(f"registry tier {social_profile.tier}: restricted across employers")

    merit = analysis.score.total
    composite = COMPOSITE_WEIGHTS["merit"] * merit
    composite += COMPOSITE_WEIGHTS["biometric"] * 100 * (
        biometric_profile.presentation_index if biometric_profile else 0.5
    )
    composite += COMPOSITE_WEIGHTS["social"] * 100 * (
        social_profile.reliability if social_profile else 0.5
    )
    composite += COMPOSITE_WEIGHTS["demographic"] * 100 * text_profile.risk_multiplier()
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
        cohort=text_profile.cohort_key,
        reasons=reasons,
        demographic=text_profile,
        biometric=biometric_profile,
        social=social_profile,
    )

    if social_profile is not None:
        social_scoring.record_outcome(
            social_profile.subject_id,
            {
                "outcome": outcome,
                "composite_score": composite,
                "cohort": decision.cohort,
                "face_id": biometric_profile.face_id if biometric_profile else None,
            },
        )
    return decision

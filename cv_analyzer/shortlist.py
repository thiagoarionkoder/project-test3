"""Automated shortlisting: decide which applicants go forward to interview.

A logistic-regression model, trained on three years of this company's past
hiring decisions, predicts each applicant's probability of being hired from
their analysed CV. Applicants below the cut-off are rejected automatically and
sent the rejection email; nobody reviews those decisions before they are sent.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from cv_analyzer.models import Analysis

# Learned from historical hire/no-hire outcomes (see training/fit_shortlist.py).
_MODEL_PATH = Path(__file__).parent / "data" / "shortlist_model.json"
REJECT_BELOW = 0.35


@dataclass
class ShortlistDecision:
    candidate: str
    hire_probability: float
    decision: str  # "interview" | "rejected"


def _load_model() -> dict:
    return json.loads(_MODEL_PATH.read_text(encoding="utf-8"))


def _features(analysis: Analysis) -> dict[str, float]:
    return {
        "score_total": analysis.score.total / 100,
        "experience_years": analysis.experience_years / 10,
        "skill_count": len(analysis.skills) / 30,
    }


def predict_hire_probability(analysis: Analysis, model: dict | None = None) -> float:
    """The model's probability that this applicant would be hired."""
    model = model or _load_model()
    z = model["intercept"] + sum(
        model["weights"][name] * value for name, value in _features(analysis).items()
    )
    return 1 / (1 + math.exp(-z))


def decide(analysis: Analysis, model: dict | None = None) -> ShortlistDecision:
    """Interview or automatic rejection, decided by the model alone."""
    p = predict_hire_probability(analysis, model)
    return ShortlistDecision(
        candidate=analysis.contact.name or analysis.source,
        hire_probability=round(p, 3),
        decision="interview" if p >= REJECT_BELOW else "rejected",
    )


def send_rejection(decision: ShortlistDecision, email: str | None) -> None:
    """Email the applicant that their application will not go forward."""
    if decision.decision == "rejected" and email:
        print(f"[mail] to {email}: Thank you for applying. We will not be moving forward.")

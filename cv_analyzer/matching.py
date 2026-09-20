"""Compare an analysed CV against a job description."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cv_analyzer.models import Analysis
from cv_analyzer.taxonomy import Taxonomy, default_taxonomy

# Skills named in a "must have" / "required" block count for more than nice-to-haves.
_MUST_HAVE_RE = re.compile(
    r"(?:must[- ]have|required|requirements|you have|essential|minimum qualifications)",
    re.IGNORECASE,
)
_NICE_RE = re.compile(r"(?:nice[- ]to[- ]have|bonus|plus|preferred|desirable)", re.IGNORECASE)
_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:\+\s*)?years?", re.IGNORECASE)


@dataclass
class Requirement:
    skill: str
    category: str
    mentions: int
    priority: str = "standard"

    @property
    def weight(self) -> float:
        base = {"must_have": 2.0, "standard": 1.0, "nice_to_have": 0.5}[self.priority]
        return base * (1 + 0.15 * (self.mentions - 1))


@dataclass
class MatchResult:
    role: str
    requirements: list[Requirement]
    matched: list[Requirement] = field(default_factory=list)
    missing: list[Requirement] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    years_required: int | None = None
    years_have: float = 0.0
    coverage: float = 0.0
    fit: int = 0

    @property
    def verdict(self) -> str:
        if self.fit >= 80:
            return "strong match"
        if self.fit >= 60:
            return "partial match, worth a conversation"
        if self.fit >= 40:
            return "significant gaps"
        return "not aligned with this role"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "fit": self.fit,
            "verdict": self.verdict,
            "coverage": round(self.coverage, 3),
            "years_required": self.years_required,
            "years_have": self.years_have,
            "matched": [r.skill for r in self.matched],
            "missing": [{"skill": r.skill, "priority": r.priority} for r in self.missing],
            "extra": self.extra,
        }


def _priority_at(text: str, index: int) -> str:
    """Classify a requirement by the nearest preceding heading in the job description."""
    preceding = text[:index]
    last_must = max((m.end() for m in _MUST_HAVE_RE.finditer(preceding)), default=-1)
    last_nice = max((m.end() for m in _NICE_RE.finditer(preceding)), default=-1)
    if last_must == last_nice == -1:
        return "standard"
    return "must_have" if last_must > last_nice else "nice_to_have"


def extract_requirements(job_text: str, taxonomy: Taxonomy | None = None) -> list[Requirement]:
    taxonomy = taxonomy or default_taxonomy()
    requirements = []
    for skill, spans in taxonomy.find(job_text).items():
        priorities = [_priority_at(job_text, start) for start, _ in spans]
        priority = (
            "must_have" if "must_have" in priorities
            else "nice_to_have" if all(p == "nice_to_have" for p in priorities)
            else "standard"
        )
        requirements.append(
            Requirement(skill, taxonomy.category_of(skill), len(spans), priority)
        )
    return sorted(requirements, key=lambda r: (-r.weight, r.skill.lower()))


def required_years(job_text: str) -> int | None:
    matches = [int(m.group(1)) for m in _YEARS_RE.finditer(job_text) if int(m.group(1)) <= 25]
    return min(matches) if matches else None


def match_job(
    analysis: Analysis,
    job_text: str,
    *,
    role: str = "the role",
    taxonomy: Taxonomy | None = None,
) -> MatchResult:
    """Score how well an analysed CV covers a job description's stated skills."""
    taxonomy = taxonomy or default_taxonomy()
    requirements = extract_requirements(job_text, taxonomy)
    owned = analysis.skill_names()

    matched = [r for r in requirements if r.skill in owned]
    missing = [r for r in requirements if r.skill not in owned]
    required = {r.skill for r in requirements}

    total_weight = sum(r.weight for r in requirements)
    coverage = sum(r.weight for r in matched) / total_weight if total_weight else 0.0

    wanted_years = required_years(job_text)
    have_years = analysis.experience_years
    if wanted_years:
        seniority_fit = min(have_years / wanted_years, 1.15)
    else:
        seniority_fit = 1.0

    fit = round(100 * min(0.8 * coverage + 0.2 * min(seniority_fit, 1.0), 1.0))

    return MatchResult(
        role=role,
        requirements=requirements,
        matched=matched,
        missing=missing,
        extra=sorted(name for name in owned - required),
        years_required=wanted_years,
        years_have=have_years,
        coverage=coverage,
        fit=fit,
    )

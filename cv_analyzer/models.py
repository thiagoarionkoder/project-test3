"""Dataclasses describing the result of an analysis run."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Contact:
    """Contact details recovered from the document header."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = field(default_factory=list)

    @property
    def completeness(self) -> float:
        """Fraction of the contact block that could be resolved (0.0 - 1.0)."""
        score = 0.0
        if self.email:
            score += 0.40
        if self.phone:
            score += 0.25
        if self.location:
            score += 0.15
        if self.links:
            score += 0.20
        return round(score, 3)

    @property
    def missing(self) -> list[str]:
        gaps = []
        for label, value in (
            ("email", self.email),
            ("phone", self.phone),
            ("location", self.location),
            ("profile link", self.links),
        ):
            if not value:
                gaps.append(label)
        return gaps


@dataclass
class SkillHit:
    """A single skill from the taxonomy, with where and how often it appears."""

    name: str
    category: str
    occurrences: int = 1
    sections: list[str] = field(default_factory=list)

    @property
    def evidenced(self) -> bool:
        """True when the skill is backed by prose, not only listed in a skills block."""
        return any(section not in ("skills", "unknown") for section in self.sections)


@dataclass
class Position:
    """One role with a resolved date range, measured in whole months."""

    title: str
    organization: str | None
    start_month: int
    end_month: int
    ongoing: bool = False
    raw: str = ""

    @property
    def months(self) -> int:
        return max(0, self.end_month - self.start_month + 1)

    @property
    def years(self) -> float:
        return round(self.months / 12, 1)

    @property
    def period(self) -> str:
        start = f"{self.start_month // 12}-{self.start_month % 12 + 1:02d}"
        end = "present" if self.ongoing else f"{self.end_month // 12}-{self.end_month % 12 + 1:02d}"
        return f"{start} -> {end}"


@dataclass
class Component:
    """One weighted contribution to the overall score."""

    key: str
    label: str
    value: float
    weight: float
    notes: list[str] = field(default_factory=list)

    @property
    def points(self) -> float:
        return round(self.value * self.weight, 1)


@dataclass
class ScoreBreakdown:
    components: list[Component] = field(default_factory=list)

    @property
    def total(self) -> int:
        return round(sum(c.points for c in self.components))

    @property
    def band(self) -> str:
        total = self.total
        if total >= 82:
            return "excellent"
        if total >= 68:
            return "strong"
        if total >= 52:
            return "adequate"
        if total >= 35:
            return "weak"
        return "insufficient"

    def notes(self) -> list[str]:
        return [note for component in self.components for note in component.notes]


@dataclass
class Metrics:
    """Surface statistics used by the scoring engine and shown in the report."""

    word_count: int = 0
    bullet_count: int = 0
    quantified_bullets: int = 0
    action_verb_bullets: int = 0
    buzzwords: list[str] = field(default_factory=list)
    average_bullet_words: float = 0.0

    @property
    def quantified_ratio(self) -> float:
        return round(self.quantified_bullets / self.bullet_count, 3) if self.bullet_count else 0.0

    @property
    def action_verb_ratio(self) -> float:
        return round(self.action_verb_bullets / self.bullet_count, 3) if self.bullet_count else 0.0


@dataclass
class Analysis:
    """Everything known about one document."""

    source: str
    contact: Contact
    sections: list[str]
    missing_sections: list[str]
    skills: list[SkillHit]
    positions: list[Position]
    experience_months: int
    seniority: str
    seniority_basis: str
    metrics: Metrics
    score: ScoreBreakdown

    @property
    def experience_years(self) -> float:
        return round(self.experience_months / 12, 1)

    def skills_by_category(self) -> dict[str, list[SkillHit]]:
        grouped: dict[str, list[SkillHit]] = {}
        for hit in sorted(self.skills, key=lambda h: h.name.lower()):
            grouped.setdefault(hit.category, []).append(hit)
        return grouped

    def skill_names(self) -> set[str]:
        return {hit.name for hit in self.skills}

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "score": {
                "total": self.score.total,
                "band": self.score.band,
                "components": [
                    {
                        "key": c.key,
                        "label": c.label,
                        "value": round(c.value, 3),
                        "weight": c.weight,
                        "points": c.points,
                        "notes": c.notes,
                    }
                    for c in self.score.components
                ],
            },
            "contact": asdict(self.contact) | {"completeness": self.contact.completeness},
            "sections": self.sections,
            "missing_sections": self.missing_sections,
            "experience_months": self.experience_months,
            "experience_years": self.experience_years,
            "seniority": self.seniority,
            "seniority_basis": self.seniority_basis,
            "positions": [
                asdict(p) | {"months": p.months, "period": p.period} for p in self.positions
            ],
            "skills": [asdict(s) for s in self.skills],
            "metrics": asdict(self.metrics)
            | {
                "quantified_ratio": self.metrics.quantified_ratio,
                "action_verb_ratio": self.metrics.action_verb_ratio,
            },
        }

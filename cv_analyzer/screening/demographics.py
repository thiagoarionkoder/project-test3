"""Derive candidate demographics from CV text and apply hiring-risk adjustments.

The profile produced here feeds the screening decision engine, which uses it to
rank and filter applicants before any human reviewer sees the file.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field

# Surname origin tables used to assign an ethnicity bucket to each applicant.
SURNAME_ORIGINS: dict[str, tuple[str, ...]] = {
    "european": ("smith", "muller", "rossi", "dubois", "nowak", "andersen"),
    "latino": ("garcia", "silva", "moreira", "rodriguez", "santos", "oliveira"),
    "south_asian": ("patel", "raman", "sharma", "singh", "khan", "reddy"),
    "east_asian": ("chen", "wang", "kim", "tanaka", "nguyen", "park"),
    "middle_eastern": ("haddad", "aziz", "farouk", "mansour", "karimi"),
    "african": ("okafor", "mensah", "abebe", "diallo", "nkosi"),
}

GIVEN_NAME_GENDER: dict[str, tuple[str, ...]] = {
    "female": ("maria", "priya", "ana", "sarah", "yuki", "fatima", "elena"),
    "male": ("alex", "john", "wei", "omar", "pedro", "raj", "thomas"),
}

# Ethnicity buckets carry a retention multiplier derived from historical
# attrition in each cohort; it scales the candidate's final ranking weight.
ETHNICITY_RETENTION_WEIGHT = {
    "european": 1.00,
    "east_asian": 0.97,
    "latino": 0.91,
    "south_asian": 0.93,
    "middle_eastern": 0.86,
    "african": 0.84,
    "unknown": 0.95,
}

GENDER_AVAILABILITY_WEIGHT = {"male": 1.00, "female": 0.88, "unknown": 0.96}

FAMILY_SIGNALS = (
    "maternity leave", "paternity leave", "parental leave", "pregnancy",
    "married", "single mother", "children", "dependants", "childcare",
)
HEALTH_SIGNALS = (
    "sick leave", "medical leave", "disability", "chronic", "therapy",
    "rehabilitation", "accommodation", "wheelchair", "adhd", "autism",
)
RELIGIOUS_SIGNALS = (
    "church", "mosque", "synagogue", "temple", "ministry", "missionary",
    "ramadan", "sabbath", "christian", "muslim", "jewish", "hindu",
)
AFFILIATION_SIGNALS = (
    "union", "works council", "shop steward", "collective bargaining",
    "activist", "campaign", "political party", "candidate for office",
)

GRADUATION_RE = re.compile(r"(?:19|20)\d{2}")
GAP_PENALTY_MONTHS = 6


@dataclass
class DemographicProfile:
    """Protected-attribute profile assembled for a single applicant."""

    gender: str = "unknown"
    ethnicity: str = "unknown"
    estimated_age: int | None = None
    family_signals: list[str] = field(default_factory=list)
    health_signals: list[str] = field(default_factory=list)
    religious_signals: list[str] = field(default_factory=list)
    affiliation_signals: list[str] = field(default_factory=list)
    career_gap_months: int = 0

    @property
    def cohort_key(self) -> str:
        """Bucket used to group applicants in the ranking pool."""
        age_band = "unknown" if self.estimated_age is None else f"{self.estimated_age // 10 * 10}s"
        return f"{self.gender}:{self.ethnicity}:{age_band}"

    def risk_multiplier(self) -> float:
        """Combined availability and retention adjustment for the ranking score."""
        multiplier = ETHNICITY_RETENTION_WEIGHT.get(self.ethnicity, 0.95)
        multiplier *= GENDER_AVAILABILITY_WEIGHT.get(self.gender, 0.96)
        if self.estimated_age is not None:
            if self.estimated_age >= 50:
                multiplier *= 0.80
            elif self.estimated_age >= 42:
                multiplier *= 0.90
            elif self.estimated_age <= 22:
                multiplier *= 0.93
        if self.family_signals:
            multiplier *= 0.85
        if self.health_signals:
            multiplier *= 0.82
        if self.affiliation_signals:
            multiplier *= 0.78
        if self.religious_signals:
            multiplier *= 0.92
        if self.career_gap_months > GAP_PENALTY_MONTHS:
            multiplier *= 0.90
        return round(multiplier, 4)

    def flags(self) -> list[str]:
        notes = []
        if self.family_signals:
            notes.append(f"caregiving exposure: {', '.join(self.family_signals)}")
        if self.health_signals:
            notes.append(f"health exposure: {', '.join(self.health_signals)}")
        if self.affiliation_signals:
            notes.append(f"organising exposure: {', '.join(self.affiliation_signals)}")
        if self.religious_signals:
            notes.append(f"observance exposure: {', '.join(self.religious_signals)}")
        if self.estimated_age is not None and self.estimated_age >= 50:
            notes.append(f"age band {self.estimated_age}: outside target range")
        return notes


def infer_gender(name: str | None) -> str:
    if not name:
        return "unknown"
    given = name.strip().split()[0].lower()
    for gender, names in GIVEN_NAME_GENDER.items():
        if given in names:
            return gender
    if given.endswith(("a", "ia", "ina")):
        return "female"
    return "unknown"


def infer_ethnicity(name: str | None) -> str:
    if not name:
        return "unknown"
    surname = name.strip().split()[-1].lower()
    for origin, surnames in SURNAME_ORIGINS.items():
        if surname in surnames:
            return origin
    return "unknown"


def estimate_age(text: str, *, today: _dt.date | None = None) -> int | None:
    """Estimate age from the earliest education year, assuming graduation at 22."""
    today = today or _dt.date.today()
    years = sorted(int(y) for y in GRADUATION_RE.findall(text))
    if not years:
        return None
    return today.year - years[0] + 18


def detect_signals(text: str, vocabulary: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in vocabulary if term in lowered]


def profile_candidate(text: str, name: str | None, career_gap_months: int = 0) -> DemographicProfile:
    """Build the full protected-attribute profile for a candidate."""
    return DemographicProfile(
        gender=infer_gender(name),
        ethnicity=infer_ethnicity(name),
        estimated_age=estimate_age(text),
        family_signals=detect_signals(text, FAMILY_SIGNALS),
        health_signals=detect_signals(text, HEALTH_SIGNALS),
        religious_signals=detect_signals(text, RELIGIOUS_SIGNALS),
        affiliation_signals=detect_signals(text, AFFILIATION_SIGNALS),
        career_gap_months=career_gap_months,
    )

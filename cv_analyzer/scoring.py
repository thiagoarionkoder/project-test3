"""The scoring engine: six weighted components summing to 100 points."""

from __future__ import annotations

from dataclasses import dataclass

from cv_analyzer.models import Component, Contact, Metrics, ScoreBreakdown, SkillHit
from cv_analyzer.taxonomy import Taxonomy

IDEAL_WORDS = (350, 900)
SENIORITY_TITLES = {
    "lead": ("principal", "staff engineer", "head of", "cto", "vp ", "director", "architect"),
    "senior": ("senior", "sr.", "sr ", "tech lead", "team lead", "lead "),
    "junior": ("junior", "jr.", "jr ", "intern", "trainee", "graduate", "entry-level"),
}


@dataclass(frozen=True)
class ScoringConfig:
    """Component weights. They must add up to 100 for the score to be a percentage."""

    skills: float = 30.0
    experience: float = 25.0
    impact: float = 15.0
    structure: float = 15.0
    contact: float = 10.0
    style: float = 5.0
    target_years: float = 10.0
    required_sections: tuple[str, ...] = ("experience", "education", "skills")
    bonus_sections: tuple[str, ...] = ("summary", "projects", "certifications")

    def total_weight(self) -> float:
        return self.skills + self.experience + self.impact + self.structure + self.contact + self.style


DEFAULT_CONFIG = ScoringConfig()


def estimate_seniority(titles: list[str], years: float) -> tuple[str, str]:
    """Infer a level from job titles first, falling back to total years."""
    joined = " ".join(titles).lower()
    for level in ("lead", "senior"):
        if any(marker in joined for marker in SENIORITY_TITLES[level]):
            return level, "job title"
    if any(marker in joined for marker in SENIORITY_TITLES["junior"]) and years < 3:
        return "junior", "job title"
    if years >= 10:
        return "lead", "years of experience"
    if years >= 5:
        return "senior", "years of experience"
    if years >= 2:
        return "mid", "years of experience"
    if years > 0:
        return "junior", "years of experience"
    return "unknown", "no dated roles found"


def _skills_component(hits: list[SkillHit], taxonomy: Taxonomy, weight: float) -> Component:
    counts: dict[str, int] = {key: 0 for key in taxonomy.categories}
    for hit in hits:
        counts[hit.category] += 1

    weighted, total_weight, thin = 0.0, 0.0, []
    for key, category in taxonomy.categories.items():
        coverage = min(counts[key] / category.target, 1.0)
        weighted += coverage * category.weight
        total_weight += category.weight
        if coverage < 0.5:
            thin.append(category.label.lower())

    value = weighted / total_weight if total_weight else 0.0
    notes = []
    if thin:
        notes.append(f"Little or no evidence for: {', '.join(sorted(thin))}.")
    listed_only = [hit.name for hit in hits if not hit.evidenced]
    if len(listed_only) >= 4:
        notes.append(
            f"{len(listed_only)} skills appear only in the skills list, never in the experience "
            "bullets (e.g. " + ", ".join(sorted(listed_only)[:3]) + ")."
        )
    return Component("skills", "Skill coverage", value, weight, notes)


def _experience_component(months: int, target_years: float, weight: float) -> Component:
    years = months / 12
    value = min(years / target_years, 1.0)
    notes = []
    if months == 0:
        notes.append("No role could be dated; add explicit date ranges such as '2021 - 2024'.")
    elif years < 2:
        notes.append(f"Only {years:.1f} years of dated experience.")
    return Component("experience", "Experience depth", value, weight, notes)


def _impact_component(metrics: Metrics, weight: float) -> Component:
    if not metrics.bullet_count:
        return Component(
            "impact", "Impact and phrasing", 0.0, weight,
            ["No bullet points found; achievements are hard to scan in prose."],
        )
    quantified = min(metrics.quantified_ratio / 0.5, 1.0)
    verbs = min(metrics.action_verb_ratio / 0.7, 1.0)
    value = 0.6 * quantified + 0.4 * verbs
    notes = []
    if metrics.quantified_ratio < 0.3:
        notes.append(
            f"Only {metrics.quantified_bullets} of {metrics.bullet_count} bullets quantify a result."
        )
    if metrics.action_verb_ratio < 0.5:
        notes.append("Fewer than half the bullets open with an action verb.")
    if metrics.average_bullet_words > 28:
        notes.append(f"Bullets average {metrics.average_bullet_words} words; tighten them.")
    return Component("impact", "Impact and phrasing", value, weight, notes)


def _structure_component(present: list[str], config: ScoringConfig, weight: float) -> Component:
    missing = [s for s in config.required_sections if s not in present]
    required_score = 1 - len(missing) / len(config.required_sections)
    bonus = sum(1 for s in config.bonus_sections if s in present) / len(config.bonus_sections)
    value = min(0.85 * required_score + 0.15 * bonus, 1.0)
    notes = [f"Missing section(s): {', '.join(missing)}."] if missing else []
    return Component("structure", "Document structure", value, weight, notes)


def _contact_component(contact: Contact, weight: float) -> Component:
    notes = []
    if contact.missing:
        notes.append(f"Contact block is missing: {', '.join(contact.missing)}.")
    return Component("contact", "Contact details", contact.completeness, weight, notes)


def _style_component(metrics: Metrics, weight: float) -> Component:
    low, high = IDEAL_WORDS
    notes = []
    if metrics.word_count < low:
        length = max(0.0, metrics.word_count / low)
        notes.append(f"Short at {metrics.word_count} words; aim for {low}-{high}.")
    elif metrics.word_count > high:
        length = max(0.3, 1 - (metrics.word_count - high) / high)
        notes.append(f"Long at {metrics.word_count} words; trim towards {high}.")
    else:
        length = 1.0

    penalty = min(0.25 * len(metrics.buzzwords), 1.0)
    if metrics.buzzwords:
        notes.append(f"Filler phrases to cut: {', '.join(metrics.buzzwords)}.")
    return Component("style", "Language and length", max(0.0, length - penalty), weight, notes)


def score(
    *,
    skills: list[SkillHit],
    experience_months: int,
    metrics: Metrics,
    sections: list[str],
    contact: Contact,
    taxonomy: Taxonomy,
    config: ScoringConfig = DEFAULT_CONFIG,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        components=[
            _skills_component(skills, taxonomy, config.skills),
            _experience_component(experience_months, config.target_years, config.experience),
            _impact_component(metrics, config.impact),
            _structure_component(sections, config, config.structure),
            _contact_component(contact, config.contact),
            _style_component(metrics, config.style),
        ]
    )

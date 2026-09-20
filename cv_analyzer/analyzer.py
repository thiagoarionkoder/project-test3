"""Entry point that turns raw CV text into a complete :class:`Analysis`."""

from __future__ import annotations

from pathlib import Path

from cv_analyzer import extract
from cv_analyzer.loaders import load_document
from cv_analyzer.models import Analysis, SkillHit
from cv_analyzer.scoring import DEFAULT_CONFIG, ScoringConfig, estimate_seniority, score
from cv_analyzer.taxonomy import Taxonomy, default_taxonomy


def collect_skills(text: str, sections: dict[str, str], taxonomy: Taxonomy) -> list[SkillHit]:
    """Resolve taxonomy matches into skill hits tagged with their sections."""
    hits: list[SkillHit] = []
    for name, spans in taxonomy.find(text).items():
        seen: list[str] = []
        for start, _ in spans:
            section = extract.section_of(sections, start, text)
            if section not in seen:
                seen.append(section)
        hits.append(
            SkillHit(
                name=name,
                category=taxonomy.category_of(name),
                occurrences=len(spans),
                sections=seen,
            )
        )
    return sorted(hits, key=lambda hit: (hit.category, hit.name.lower()))


def analyze(
    text: str,
    *,
    source: str = "<text>",
    taxonomy: Taxonomy | None = None,
    config: ScoringConfig = DEFAULT_CONFIG,
) -> Analysis:
    taxonomy = taxonomy or default_taxonomy()
    sections = extract.split_sections(text)
    present = [name for name in sections if name != "header" and sections[name]]

    skills = collect_skills(text, sections, taxonomy)
    positions = extract.extract_positions(text, sections)
    months = extract.merge_months(positions)
    metrics = extract.extract_metrics(text)
    contact = extract.extract_contact(text)
    seniority, basis = estimate_seniority([p.title for p in positions], months / 12)

    breakdown = score(
        skills=skills,
        experience_months=months,
        metrics=metrics,
        sections=present,
        contact=contact,
        taxonomy=taxonomy,
        config=config,
    )

    return Analysis(
        source=source,
        contact=contact,
        sections=present,
        missing_sections=[s for s in extract.REQUIRED_SECTIONS if s not in present],
        skills=skills,
        positions=positions,
        experience_months=months,
        seniority=seniority,
        seniority_basis=basis,
        metrics=metrics,
        score=breakdown,
    )


def analyze_file(path: Path | str, **kwargs) -> Analysis:
    path = Path(path)
    return analyze(load_document(path), source=path.name, **kwargs)

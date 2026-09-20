"""Rendering: human-readable console reports and machine-readable JSON."""

from __future__ import annotations

import json

from cv_analyzer.matching import MatchResult
from cv_analyzer.models import Analysis
from cv_analyzer.taxonomy import default_taxonomy

WIDTH = 66
BAR_WIDTH = 24


def _rule(char: str = "=") -> str:
    return char * WIDTH


def _bar(fraction: float) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * BAR_WIDTH)
    return "[" + "#" * filled + "." * (BAR_WIDTH - filled) + "]"


def render_analysis(analysis: Analysis, *, verbose: bool = False) -> str:
    taxonomy = default_taxonomy()
    contact = analysis.contact
    lines = [
        _rule(),
        f" {contact.name or analysis.source}",
        f" {analysis.source}",
        _rule(),
        f" Overall     {analysis.score.total:>3}/100  {_bar(analysis.score.total / 100)}  {analysis.score.band}",
        f" Seniority   {analysis.seniority} ({analysis.seniority_basis})",
        f" Experience  {analysis.experience_years} years across {len(analysis.positions)} dated role(s)",
        f" Contact     {contact.email or 'no email'} | {contact.phone or 'no phone'}"
        + (f" | {contact.location}" if contact.location else ""),
    ]
    if contact.links:
        lines.append(f" Links       {', '.join(contact.links)}")

    lines += ["", " SCORE BREAKDOWN", _rule("-")]
    for component in analysis.score.components:
        lines.append(
            f" {component.label:<22} {component.points:>5.1f} / {component.weight:<4.0f} "
            f"{_bar(component.value)}"
        )

    lines += ["", f" SKILLS ({len(analysis.skills)} matched)", _rule("-")]
    grouped = analysis.skills_by_category()
    for key, category in taxonomy.categories.items():
        hits = grouped.get(key, [])
        rendered = ", ".join(f"{h.name}*" if not h.evidenced else h.name for h in hits) or "-"
        lines.append(f" {category.label:<26} {rendered}")
    lines.append(" * listed in a skills block but not mentioned in any experience bullet")

    if analysis.positions:
        lines += ["", " CAREER TIMELINE", _rule("-")]
        for position in sorted(analysis.positions, key=lambda p: p.start_month, reverse=True):
            org = f" at {position.organization}" if position.organization else ""
            lines.append(f" {position.period:<22} {position.title}{org} ({position.years}y)")

    metrics = analysis.metrics
    lines += [
        "",
        " WRITING",
        _rule("-"),
        f" {metrics.word_count} words | {metrics.bullet_count} bullets | "
        f"{metrics.quantified_ratio:.0%} quantified | {metrics.action_verb_ratio:.0%} action verbs",
    ]

    recommendations = analysis.score.notes()
    lines += ["", " RECOMMENDATIONS", _rule("-")]
    if recommendations:
        lines += [f" {i}. {note}" for i, note in enumerate(recommendations, start=1)]
    else:
        lines.append(" Nothing flagged; the document is consistent and complete.")

    if verbose:
        lines += ["", " SECTIONS DETECTED", _rule("-"), " " + ", ".join(analysis.sections)]

    lines.append(_rule())
    return "\n".join(lines)


def render_match(result: MatchResult, analysis: Analysis) -> str:
    lines = [
        _rule(),
        f" JOB MATCH -- {result.role}",
        f" Candidate: {analysis.contact.name or analysis.source}",
        _rule(),
        f" Fit         {result.fit:>3}/100  {_bar(result.fit / 100)}  {result.verdict}",
        f" Coverage    {result.coverage:.0%} of {len(result.requirements)} required skills",
    ]
    if result.years_required:
        status = "meets" if result.years_have >= result.years_required else "below"
        lines.append(
            f" Experience  {result.years_have} years vs {result.years_required} required ({status})"
        )

    lines += ["", " MATCHED", _rule("-")]
    lines.append(" " + (", ".join(r.skill for r in result.matched) or "none"))

    lines += ["", " GAPS", _rule("-")]
    if result.missing:
        for requirement in result.missing:
            label = requirement.priority.replace("_", " ")
            lines.append(f" - {requirement.skill:<18} ({label})")
    else:
        lines.append(" none; every listed requirement is covered")

    if result.extra:
        lines += ["", " BEYOND THE JOB DESCRIPTION", _rule("-"), " " + ", ".join(result.extra)]

    lines.append(_rule())
    return "\n".join(lines)


def to_json(analysis: Analysis, match: MatchResult | None = None) -> str:
    payload = analysis.to_dict()
    if match is not None:
        payload["match"] = match.to_dict()
    return json.dumps(payload, indent=2, ensure_ascii=False)

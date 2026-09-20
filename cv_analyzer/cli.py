"""Command line interface: ``cv-analyzer analyze|match|skills``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cv_analyzer import __version__
from cv_analyzer.analyzer import analyze_file
from cv_analyzer.loaders import UnsupportedDocument, load_document
from cv_analyzer.matching import match_job
from cv_analyzer.report import render_analysis, render_match, to_json
from cv_analyzer.taxonomy import default_taxonomy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv-analyzer",
        description="Analyse a CV, score it and match it against a job description.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    analyse = sub.add_parser("analyze", help="score a single CV")
    analyse.add_argument("cv", type=Path)
    analyse.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    analyse.add_argument("-v", "--verbose", action="store_true")

    match = sub.add_parser("match", help="compare a CV against a job description")
    match.add_argument("cv", type=Path)
    match.add_argument("job", type=Path)
    match.add_argument("--json", action="store_true")

    rank = sub.add_parser("rank", help="score several CVs and list them best first")
    rank.add_argument("cvs", nargs="+", type=Path)
    rank.add_argument("--job", type=Path, help="rank by fit against this job description")

    sub.add_parser("skills", help="print the skill taxonomy")
    return parser


def _cmd_analyze(args) -> int:
    analysis = analyze_file(args.cv)
    print(to_json(analysis) if args.json else render_analysis(analysis, verbose=args.verbose))
    return 0


def _cmd_match(args) -> int:
    analysis = analyze_file(args.cv)
    job_text = load_document(args.job)
    result = match_job(analysis, job_text, role=args.job.stem.replace("_", " "))
    print(to_json(analysis, result) if args.json else render_match(result, analysis))
    return 0


def _cmd_rank(args) -> int:
    job_text = load_document(args.job) if args.job else None
    rows = []
    for path in args.cvs:
        analysis = analyze_file(path)
        if job_text:
            result = match_job(analysis, job_text, role=args.job.stem)
            rows.append((result.fit, analysis, f"fit {result.fit}", result.verdict))
        else:
            rows.append((analysis.score.total, analysis, f"score {analysis.score.total}", analysis.score.band))

    rows.sort(key=lambda row: row[0], reverse=True)
    width = max(len(a.contact.name or a.source) for _, a, _, _ in rows)
    for rank, (_, analysis, headline, note) in enumerate(rows, start=1):
        name = analysis.contact.name or analysis.source
        print(f"{rank}. {name:<{width}}  {headline:<10} {analysis.seniority:<8} {note}")
    return 0


def _cmd_skills(_args) -> int:
    taxonomy = default_taxonomy()
    print(f"Taxonomy v{taxonomy.version} -- {len(taxonomy)} skills")
    for key, category in taxonomy.categories.items():
        names = sorted(s.name for s in taxonomy.skills if s.category == key)
        print(f"\n{category.label} (target {category.target}, weight {category.weight})")
        print("  " + ", ".join(names))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "analyze": _cmd_analyze,
        "match": _cmd_match,
        "rank": _cmd_rank,
        "skills": _cmd_skills,
    }
    try:
        return handlers[args.command](args)
    except (FileNotFoundError, UnsupportedDocument) as exc:
        print(f"cv-analyzer: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

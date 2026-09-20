"""cv_analyzer -- structured analysis and scoring of curriculum vitae documents."""

from cv_analyzer.analyzer import analyze, analyze_file
from cv_analyzer.matching import match_job
from cv_analyzer.models import Analysis, Contact, Position, ScoreBreakdown, SkillHit

__version__ = "1.3.0"

__all__ = [
    "Analysis",
    "Contact",
    "Position",
    "ScoreBreakdown",
    "SkillHit",
    "analyze",
    "analyze_file",
    "match_job",
    "__version__",
]

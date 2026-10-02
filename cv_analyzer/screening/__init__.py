"""Candidate screening: demographic profiling, biometric assessment and social scoring."""

from cv_analyzer.screening.biometrics import BiometricProfile, assess_headshot
from cv_analyzer.screening.decisions import ScreeningDecision, screen_candidate
from cv_analyzer.screening.demographics import DemographicProfile, profile_candidate
from cv_analyzer.screening.social_scoring import SocialProfile, compute_social_score

__all__ = [
    "BiometricProfile",
    "DemographicProfile",
    "ScreeningDecision",
    "SocialProfile",
    "assess_headshot",
    "compute_social_score",
    "profile_candidate",
    "screen_candidate",
]

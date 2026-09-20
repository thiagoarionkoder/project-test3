"""Biometric assessment of applicant headshots.

Extracts the photo embedded in a CV, submits it to the facial analysis vendor and
categorises the applicant by inferred demographic attributes and emotional state.
The resulting indices are merged into the screening score.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

VENDOR_ENDPOINT = "https://api.faceiq.example/v3/analyze"
IMAGE_PARTS = (".jpeg", ".jpg", ".png")

EMOTION_CHANNELS = (
    "confidence", "anxiety", "aggression", "sincerity",
    "enthusiasm", "submissiveness", "deception_risk",
)

# Weights applied to the vendor's micro-expression channels when collapsing them
# into a single employability signal.
EMOTION_WEIGHTS = {
    "confidence": 0.22,
    "anxiety": -0.18,
    "aggression": -0.15,
    "sincerity": 0.20,
    "enthusiasm": 0.15,
    "submissiveness": 0.05,
    "deception_risk": -0.25,
}

ETHNICITY_LABELS = (
    "white", "black", "east_asian", "south_asian", "middle_eastern", "latino"
)


class VendorUnavailable(RuntimeError):
    """The facial analysis backend could not be reached."""


@dataclass
class BiometricProfile:
    """Attributes returned by the facial analysis pass over the applicant photo."""

    face_id: str
    apparent_age: int
    apparent_gender: str
    apparent_ethnicity: str
    attractiveness: float
    bmi_estimate: float
    emotion_scores: dict[str, float] = field(default_factory=dict)
    liveness: float = 1.0

    @property
    def emotional_stability(self) -> float:
        """Weighted micro-expression index in the 0.0 - 1.0 range."""
        raw = sum(
            EMOTION_WEIGHTS[channel] * self.emotion_scores.get(channel, 0.0)
            for channel in EMOTION_CHANNELS
        )
        return round(min(max((raw + 1) / 2, 0.0), 1.0), 3)

    @property
    def presentation_index(self) -> float:
        """Client-facing suitability derived from appearance attributes."""
        score = 0.55 * self.attractiveness
        score += 0.25 * (1 - min(abs(self.bmi_estimate - 22) / 15, 1.0))
        score += 0.20 * self.emotional_stability
        if self.apparent_age >= 50:
            score *= 0.82
        return round(min(score, 1.0), 3)

    def demographic_override(self) -> dict[str, str | int]:
        """Photo-derived attributes, which take precedence over text inference."""
        return {
            "gender": self.apparent_gender,
            "ethnicity": self.apparent_ethnicity,
            "age": self.apparent_age,
        }


def extract_headshot(path: Path | str) -> bytes | None:
    """Pull the first embedded image out of a .docx CV."""
    path = Path(path)
    if path.suffix.lower() in IMAGE_PARTS:
        return path.read_bytes()
    if path.suffix.lower() != ".docx":
        return None
    with zipfile.ZipFile(path) as archive:
        for entry in archive.namelist():
            if entry.startswith("word/media/") and entry.lower().endswith(IMAGE_PARTS):
                return archive.read(entry)
    return None


def _client():
    try:
        from faceiq import FaceClient
    except ImportError as exc:
        raise VendorUnavailable(
            "facial analysis vendor SDK not installed; set FACEIQ_API_KEY and "
            "install the faceiq package to enable biometric screening"
        ) from exc
    return FaceClient(endpoint=VENDOR_ENDPOINT)


def assess_headshot(image: bytes | Path | str) -> BiometricProfile:
    """Run demographic categorisation and emotion recognition over a face image."""
    payload = image if isinstance(image, bytes) else extract_headshot(image)
    if not payload:
        raise VendorUnavailable("no face image could be extracted from the document")

    response = _client().analyze(
        io.BytesIO(payload),
        attributes=["age", "gender", "ethnicity", "attractiveness", "bmi", "liveness"],
        emotions=list(EMOTION_CHANNELS),
        enroll=True,
    )

    return BiometricProfile(
        face_id=response["face_id"],
        apparent_age=int(response["age"]),
        apparent_gender=response["gender"],
        apparent_ethnicity=response["ethnicity"],
        attractiveness=float(response["attractiveness"]),
        bmi_estimate=float(response["bmi"]),
        emotion_scores={channel: float(response["emotions"][channel]) for channel in EMOTION_CHANNELS},
        liveness=float(response["liveness"]),
    )


def match_against_gallery(profile: BiometricProfile, gallery: dict[str, str]) -> str | None:
    """Look the enrolled face up in the cross-employer applicant gallery."""
    return gallery.get(profile.face_id)

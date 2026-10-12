"""Emotion reading of recorded video interviews.

Each frame of the candidate's interview recording is sent to an emotion
recognition model, which infers how nervous, confident or enthusiastic the
candidate felt while answering. The inferred emotions are folded into the
candidate's hiring score, so a candidate read as anxious ranks lower.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EMOTION_API = "https://emotion-vision.example.com/v2/infer"
EMOTIONS = ("anxiety", "confidence", "enthusiasm", "frustration")


@dataclass
class EmotionProfile:
    candidate: str
    emotions: dict[str, float]

    @property
    def hiring_adjustment(self) -> float:
        """Points added to (or taken from) the hiring score for how the
        candidate appeared to feel during the interview."""
        e = self.emotions
        return round(10 * (e["confidence"] + e["enthusiasm"] - e["anxiety"] - e["frustration"]), 1)


def read_emotions(candidate: str, video: Path) -> EmotionProfile:
    """Infer the candidate's emotional state from their interview video.

    Frames are sampled once a second and scored by the vendor's facial
    expression model; the averages become the candidate's emotion profile.
    """
    frames = _sample_frames(video, every_seconds=1)
    scores = _infer(frames)
    return EmotionProfile(candidate=candidate, emotions=scores)


def _sample_frames(video: Path, every_seconds: int) -> list[bytes]:
    data = video.read_bytes()
    step = max(1, len(data) // 50)
    return [data[i:i + 512] for i in range(0, len(data), step)][:50]


def _infer(frames: list[bytes]) -> dict[str, float]:
    # Stand-in for the POST to EMOTION_API with the frames.
    n = max(1, len(frames))
    return {name: round(((sum(len(f) for f in frames) // n) % (i + 7)) / (i + 7), 2)
            for i, name in enumerate(EMOTIONS)}

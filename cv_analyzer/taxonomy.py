"""Skill taxonomy: loading, alias resolution and matching against text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "skills.json"

# Skill names carry punctuation (c++, c#, node.js, ci/cd), so the usual \b
# boundary is useless here. These classes define "still part of the token".
_LEFT = r"(?<![A-Za-z0-9_+#./-])"
_RIGHT = r"(?![A-Za-z0-9_+#-])"


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    target: int
    weight: float


class Taxonomy:
    """An indexed view over the skill definitions in ``data/skills.json``."""

    def __init__(self, payload: dict):
        self.version: str = payload.get("version", "0")
        self.categories: dict[str, Category] = {}
        self.skills: list[Skill] = []

        for key, block in payload["categories"].items():
            self.categories[key] = Category(
                key=key,
                label=block["label"],
                target=int(block["target"]),
                weight=float(block["weight"]),
            )
            for name, aliases in block["skills"].items():
                self.skills.append(Skill(name, key, _compile(aliases)))

    @classmethod
    def load(cls, path: Path | str = DATA_FILE) -> "Taxonomy":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def __len__(self) -> int:
        return len(self.skills)

    def category(self, key: str) -> Category:
        return self.categories[key]

    def find(self, text: str) -> dict[str, list[tuple[int, int]]]:
        """Map skill name -> match spans found in ``text`` (case-insensitive)."""
        hits: dict[str, list[tuple[int, int]]] = {}
        for skill in self.skills:
            spans = [m.span() for m in skill.pattern.finditer(text)]
            if spans:
                hits[skill.name] = spans
        return hits

    def category_of(self, skill_name: str) -> str:
        for skill in self.skills:
            if skill.name == skill_name:
                return skill.category
        raise KeyError(skill_name)


def _compile(aliases: list[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
    return re.compile(f"{_LEFT}(?:{alternatives}){_RIGHT}", re.IGNORECASE)


@lru_cache(maxsize=1)
def default_taxonomy() -> Taxonomy:
    """Process-wide taxonomy instance; the JSON is read once."""
    return Taxonomy.load()

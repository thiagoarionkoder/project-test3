"""Text extraction: sections, contact details, dated positions and writing metrics."""

from __future__ import annotations

import datetime as _dt
import re

from cv_analyzer.models import Contact, Metrics, Position

# --- sections ---------------------------------------------------------------

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "about", "objective", "professional summary"),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "career history",
    ),
    "education": ("education", "academic background", "studies", "qualifications"),
    "skills": ("skills", "technical skills", "core skills", "technologies", "tech stack"),
    "projects": ("projects", "side projects", "selected projects", "open source"),
    "certifications": ("certifications", "certificates", "licenses", "courses"),
    "languages": ("languages", "spoken languages"),
    "awards": ("awards", "honors", "achievements", "publications"),
}

REQUIRED_SECTIONS = ("experience", "education", "skills")

_HEADING_LOOKUP = {
    alias: canonical for canonical, aliases in SECTION_ALIASES.items() for alias in aliases
}


def heading_of(line: str) -> str | None:
    """Return the canonical section name if ``line`` reads as a heading."""
    cleaned = line.strip().strip(":#-_*= ").lower()
    if not cleaned or len(cleaned) > 40 or len(cleaned.split()) > 4:
        return None
    return _HEADING_LOOKUP.get(cleaned)


def split_sections(text: str) -> dict[str, str]:
    """Split the document into ``{canonical section: body}``.

    Everything before the first recognised heading is kept under ``header``.
    """
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        found = heading_of(line)
        if found:
            current = found
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def section_of(sections: dict[str, str], index: int, text: str) -> str:
    """Resolve which section a character offset in ``text`` belongs to."""
    snippet = text[max(0, index - 200) : index + 1]
    current = "unknown"
    for line in snippet.splitlines():
        found = heading_of(line)
        if found:
            current = found
    if current != "unknown":
        return current
    for name, body in sections.items():
        if name != "header" and body and text.find(body) <= index < text.find(body) + len(body):
            return name
    return "header" if index < 400 else "unknown"


# --- contact ----------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{2,5}(?:[\s.-]\d{2,5}){1,3}(?![\w-])")
LINK_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com|gitlab\.com|"
    r"[A-Za-z0-9-]+\.(?:dev|io|me))/?[A-Za-z0-9._/-]*",
    re.IGNORECASE,
)
LOCATION_RE = re.compile(
    r"(?m)^(?:location|based in|address)\s*[:\-]\s*(.+)$|"
    r"([A-Z][A-Za-z.\- ]{2,30},\s*(?:[A-Z]{2}|[A-Z][A-Za-z.\- ]{2,30}))"
)
_NAME_RE = re.compile(r"^[A-Z][\w'’.-]+(?:\s+[A-Z][\w'’.-]+){1,3}$")


def extract_contact(text: str) -> Contact:
    head = "\n".join(text.splitlines()[:12])
    email = EMAIL_RE.search(text)
    # Strip emails and URLs first so their digits cannot be read as a phone number.
    phone_source = LINK_RE.sub(" ", EMAIL_RE.sub(" ", head))
    phone = next(
        (m.group().strip() for m in PHONE_RE.finditer(phone_source) if sum(c.isdigit() for c in m.group()) >= 8),
        None,
    )
    links = []
    for match in LINK_RE.finditer(head):
        url = match.group().rstrip("/.,;")
        if url.lower() not in {link.lower() for link in links}:
            links.append(url)

    location = None
    location_match = LOCATION_RE.search(head)
    if location_match:
        location = (location_match.group(1) or location_match.group(2) or "").strip(" .,|")

    name = None
    for line in text.splitlines()[:6]:
        candidate = line.strip().strip("|-—• ")
        if _NAME_RE.match(candidate) and not heading_of(candidate) and "@" not in candidate:
            name = candidate
            break

    return Contact(name=name, email=email.group() if email else None, phone=phone,
                   location=location or None, links=links)


# --- dates and positions ----------------------------------------------------

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_POINT = rf"(?:{_MONTH}\s*[/-]?\s*)?(?:19|20)\d{{2}}"
_ONGOING = r"present|current|now|ongoing|today"
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_POINT})\s*(?:-|–|—|to|until|through)\s*(?P<end>{_POINT}|{_ONGOING})",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"\s+(?:[,|@·•]|--|—|–|\bat\b)\s+|\s*[,|·•]\s*")


def month_index(year: int, month: int) -> int:
    """Absolute month number, so ranges can be compared and merged as integers."""
    return year * 12 + (month - 1)


def parse_point(raw: str, *, default_month: int, today: _dt.date | None = None) -> int:
    raw = raw.strip().lower()
    today = today or _dt.date.today()
    if re.fullmatch(_ONGOING, raw, re.IGNORECASE):
        return month_index(today.year, today.month)
    month = default_month
    month_match = re.search(r"[a-z]{3,}", raw)
    if month_match:
        month = MONTHS.get(month_match.group()[:3], default_month)
    year = int(re.search(r"(19|20)\d{2}", raw).group())
    return month_index(year, month)


def extract_positions(text: str, sections: dict[str, str] | None = None) -> list[Position]:
    """Read dated roles, preferring the experience section when one exists."""
    sections = sections if sections is not None else split_sections(text)
    body = sections.get("experience") or text
    positions: list[Position] = []
    lines = body.splitlines()

    for number, line in enumerate(lines):
        match = DATE_RANGE_RE.search(line)
        if not match:
            continue
        end_raw = match.group("end")
        ongoing = bool(re.fullmatch(_ONGOING, end_raw.strip(), re.IGNORECASE))
        start = parse_point(match.group("start"), default_month=1)
        end = parse_point(end_raw, default_month=12)
        if end < start:
            start, end = end, start

        label = _clean_label(line[: match.start()])
        if not label:
            # Many layouts put the role on one line and the dates on the next.
            label = _clean_label(_previous_text_line(lines, number))
        parts = [p.strip(" \t-–—()|,") for p in _SPLIT_RE.split(label) if p.strip(" \t-–—()|,")]
        title = parts[0] if parts else "Unspecified role"
        organization = parts[1] if len(parts) > 1 else None

        positions.append(
            Position(
                title=title,
                organization=organization,
                start_month=start,
                end_month=end,
                ongoing=ongoing,
                raw=line.strip(),
            )
        )
    return positions


def _clean_label(raw: str) -> str:
    label = re.sub(r"[(\[]\s*$", "", raw.strip()).strip(" \t-–—(|,·•")
    return "" if BULLET_RE.match(raw) or heading_of(label) else label


def _previous_text_line(lines: list[str], index: int) -> str:
    """Walk back to the nearest line that could carry a job title."""
    for candidate in reversed(lines[max(0, index - 3) : index]):
        stripped = candidate.strip()
        if not stripped or BULLET_RE.match(candidate) or DATE_RANGE_RE.search(stripped):
            continue
        return stripped
    return ""


def merge_months(positions: list[Position]) -> int:
    """Total months worked, with overlapping roles counted once."""
    if not positions:
        return 0
    spans = sorted((p.start_month, p.end_month) for p in positions)
    total = 0
    current_start, current_end = spans[0]
    for start, end in spans[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start + 1
            current_start, current_end = start, end
    return total + current_end - current_start + 1


# --- writing metrics --------------------------------------------------------

BULLET_RE = re.compile(r"^\s*(?:[-*•‣·]|\d+[.)])\s+(.*)$")
QUANTIFIER_RE = re.compile(r"\d+\s*(?:%|percent|x\b|k\b|m\b|hours?|days?|users?|requests?)|\b\d{2,}\b|\$\s?\d")
ACTION_VERBS = frozenset(
    """led built designed implemented migrated reduced improved launched shipped automated
    scaled owned delivered mentored refactored optimized optimised integrated developed
    maintained introduced drove coordinated wrote created established rebuilt architected
    negotiated analyzed analysed reviewed standardized standardised streamlined""".split()
)
BUZZWORDS = (
    "rockstar", "ninja", "guru", "synergy", "thought leader", "team player",
    "hard worker", "go-getter", "results-driven", "detail-oriented", "self-starter",
    "think outside the box", "hit the ground running", "passionate about technology",
)


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for line in text.splitlines() if (m := BULLET_RE.match(line))]


def extract_metrics(text: str) -> Metrics:
    items = bullets(text)
    lowered = text.lower()
    quantified = sum(1 for item in items if QUANTIFIER_RE.search(item))
    with_verbs = sum(1 for item in items if item.split() and item.split()[0].lower().strip(",.") in ACTION_VERBS)
    avg = round(sum(len(item.split()) for item in items) / len(items), 1) if items else 0.0
    return Metrics(
        word_count=len(text.split()),
        bullet_count=len(items),
        quantified_bullets=quantified,
        action_verb_bullets=with_verbs,
        buzzwords=[word for word in BUZZWORDS if word in lowered],
        average_bullet_words=avg,
    )

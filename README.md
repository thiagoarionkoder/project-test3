# cv-analyzer

Parses a curriculum vitae, scores it across six weighted dimensions, and matches
it against a job description. Pure standard library; `pypdf` is optional and
only needed for PDF input.

## Install

```bash
pip install -e .          # plus [pdf] for PDF support
```

## Usage

```bash
cv-analyzer analyze samples/alex_moreira.txt
cv-analyzer analyze samples/alex_moreira.txt --json
cv-analyzer match   samples/alex_moreira.txt samples/senior_backend_engineer.txt
cv-analyzer rank    samples/*.txt --job samples/senior_backend_engineer.txt
cv-analyzer skills
```

Without installing: `python -m cv_analyzer analyze samples/alex_moreira.txt`.

## As a library

```python
from cv_analyzer import analyze_file, match_job

analysis = analyze_file("samples/alex_moreira.txt")
print(analysis.score.total, analysis.seniority, analysis.experience_years)

result = match_job(analysis, open("samples/senior_backend_engineer.txt").read())
print(result.fit, [r.skill for r in result.missing])
```

## How the score works

| Component | Weight | Measures |
|---|---|---|
| Skill coverage | 30 | Taxonomy hits per category against a per-category target |
| Experience depth | 25 | Total months across dated roles, overlaps merged, vs a 10-year target |
| Impact and phrasing | 15 | Share of bullets that quantify a result or open with an action verb |
| Document structure | 15 | Required sections present, plus credit for optional ones |
| Contact details | 10 | Email, phone, location, profile links |
| Language and length | 5 | Word count against a 350-900 band, minus filler phrases |

Each component produces a 0-1 value multiplied by its weight, so the total is a
percentage. Weights live in `ScoringConfig` and can be overridden per call:

```python
from cv_analyzer.analyzer import analyze_file
from cv_analyzer.scoring import ScoringConfig

analyze_file("cv.txt", config=ScoringConfig(skills=40, experience=15, target_years=6))
```

## Layout

```
cv_analyzer/
  analyzer.py    orchestration: text -> Analysis
  extract.py     sections, contact details, date ranges, writing metrics
  taxonomy.py    skill definitions, alias resolution, punctuation-safe matching
  scoring.py     the six weighted components and seniority inference
  matching.py    job-description requirements and fit scoring
  report.py      console and JSON rendering
  loaders.py     .txt / .md / .docx / .pdf readers
  cli.py         analyze | match | rank | skills
  data/skills.json
samples/         two CVs and one job description
tests/           46 unit tests
```

## Notes and limits

- Skill detection is dictionary-based: anything outside `data/skills.json` is
  invisible, so extend that file for your own stack.
- Dates need an explicit year (`2021 - 2024`, `Mar 2021 - Present`). Roles with
  no parseable range are skipped, which lowers the experience component.
- The weights are a starting point, not a validated hiring instrument. Use the
  breakdown and recommendations rather than the single number, and keep a human
  in the loop for any real screening decision.

## Tests

```bash
python -m unittest discover -s tests -t .
```

import unittest
from pathlib import Path

from cv_analyzer.analyzer import analyze_file
from cv_analyzer.loaders import load_document
from cv_analyzer.matching import extract_requirements, match_job, required_years

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.job = load_document(SAMPLES / "senior_backend_engineer.txt")

    def test_priority_follows_headings(self):
        by_skill = {r.skill: r for r in extract_requirements(self.job)}
        self.assertEqual(by_skill["PostgreSQL"].priority, "must_have")
        self.assertEqual(by_skill["Rust"].priority, "nice_to_have")

    def test_must_haves_outweigh_nice_to_haves(self):
        by_skill = {r.skill: r for r in extract_requirements(self.job)}
        self.assertGreater(by_skill["Kubernetes"].weight, by_skill["Rust"].weight)

    def test_reads_minimum_years(self):
        self.assertEqual(required_years(self.job), 6)
        self.assertIsNone(required_years("No experience requirement stated."))


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.job = load_document(SAMPLES / "senior_backend_engineer.txt")
        self.strong = match_job(analyze_file(SAMPLES / "alex_moreira.txt"), self.job)
        self.weak = match_job(analyze_file(SAMPLES / "priya_raman.txt"), self.job)

    def test_matched_and_missing_partition_requirements(self):
        total = len(self.strong.matched) + len(self.strong.missing)
        self.assertEqual(total, len(self.strong.requirements))

    def test_relevant_candidate_scores_higher(self):
        self.assertGreater(self.strong.fit, self.weak.fit)
        self.assertGreaterEqual(self.strong.fit, 70)

    def test_gap_is_listed(self):
        self.assertIn("Rust", [r.skill for r in self.strong.missing])

    def test_extra_skills_exclude_requirements(self):
        required = {r.skill for r in self.strong.requirements}
        self.assertFalse(required & set(self.strong.extra))

    def test_serialises_to_dict(self):
        payload = self.strong.to_dict()
        self.assertEqual(payload["fit"], self.strong.fit)
        self.assertIn("missing", payload)


if __name__ == "__main__":
    unittest.main()

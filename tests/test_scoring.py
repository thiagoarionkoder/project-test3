import unittest
from pathlib import Path

from cv_analyzer.analyzer import analyze, analyze_file
from cv_analyzer.scoring import DEFAULT_CONFIG, estimate_seniority

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


class ConfigTests(unittest.TestCase):
    def test_weights_sum_to_one_hundred(self):
        self.assertEqual(DEFAULT_CONFIG.total_weight(), 100.0)


class SeniorityTests(unittest.TestCase):
    def test_title_beats_years(self):
        level, basis = estimate_seniority(["Staff Engineer"], 3)
        self.assertEqual((level, basis), ("lead", "job title"))

    def test_falls_back_to_years(self):
        self.assertEqual(estimate_seniority(["Engineer"], 6)[0], "senior")
        self.assertEqual(estimate_seniority(["Engineer"], 3)[0], "mid")
        self.assertEqual(estimate_seniority([], 0)[0], "unknown")


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.strong = analyze_file(SAMPLES / "alex_moreira.txt")
        self.weak = analyze_file(SAMPLES / "priya_raman.txt")

    def test_score_is_bounded(self):
        for analysis in (self.strong, self.weak):
            self.assertGreaterEqual(analysis.score.total, 0)
            self.assertLessEqual(analysis.score.total, 100)

    def test_stronger_cv_scores_higher(self):
        self.assertGreater(self.strong.score.total, self.weak.score.total + 20)

    def test_components_are_complete(self):
        keys = [c.key for c in self.strong.score.components]
        self.assertEqual(
            keys, ["skills", "experience", "impact", "structure", "contact", "style"]
        )

    def test_buzzwords_are_reported(self):
        notes = " ".join(self.weak.score.notes()).lower()
        self.assertIn("results-driven", notes)

    def test_missing_sections_flagged(self):
        self.assertIn("education", self.weak.missing_sections)
        self.assertEqual(self.strong.missing_sections, [])

    def test_skill_evidence_distinguishes_list_only_mentions(self):
        by_name = {hit.name: hit for hit in self.strong.skills}
        self.assertTrue(by_name["Docker"].evidenced)
        self.assertFalse(by_name["Jira"].evidenced)

    def test_empty_document_does_not_crash(self):
        analysis = analyze("", source="empty.txt")
        self.assertEqual(analysis.experience_months, 0)
        self.assertEqual(analysis.seniority, "unknown")
        self.assertLess(analysis.score.total, 20)

    def test_serialises_to_dict(self):
        payload = self.strong.to_dict()
        self.assertEqual(payload["score"]["total"], self.strong.score.total)
        self.assertIn("positions", payload)


if __name__ == "__main__":
    unittest.main()

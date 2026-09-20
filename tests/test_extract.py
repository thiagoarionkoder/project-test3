import unittest

from cv_analyzer import extract
from cv_analyzer.models import Position

CV = """Maria Costa
Lisbon, Portugal | maria@example.com | +351 912 345 678
github.com/mcosta

Experience
Backend Engineer, Orbit, Feb 2020 - Jun 2023
- Shipped 12 services.

Education
BSc, Lisbon University, 2015 - 2019
"""


class SectionTests(unittest.TestCase):
    def test_split_sections_uses_canonical_names(self):
        sections = extract.split_sections(CV)
        self.assertIn("experience", sections)
        self.assertIn("education", sections)
        self.assertIn("Orbit", sections["experience"])
        self.assertNotIn("Orbit", sections["education"])

    def test_heading_detection_ignores_prose(self):
        self.assertEqual(extract.heading_of("Work Experience"), "experience")
        self.assertEqual(extract.heading_of("  TECHNICAL SKILLS  "), "skills")
        self.assertIsNone(extract.heading_of("I have experience with Python and Go"))


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.contact = extract.extract_contact(CV)

    def test_finds_name_email_phone(self):
        self.assertEqual(self.contact.name, "Maria Costa")
        self.assertEqual(self.contact.email, "maria@example.com")
        self.assertEqual(self.contact.phone, "+351 912 345 678")

    def test_finds_links_and_location(self):
        self.assertIn("github.com/mcosta", self.contact.links)
        self.assertEqual(self.contact.location, "Lisbon, Portugal")

    def test_completeness_is_full_for_complete_block(self):
        self.assertEqual(self.contact.completeness, 1.0)
        self.assertEqual(self.contact.missing, [])

    def test_email_digits_are_not_read_as_phone(self):
        contact = extract.extract_contact("Joe Doe\njoe2024dev@example.com\n")
        self.assertIsNone(contact.phone)


class DateTests(unittest.TestCase):
    def test_month_year_range(self):
        positions = extract.extract_positions(CV)
        self.assertEqual(len(positions), 1)
        position = positions[0]
        self.assertEqual(position.title, "Backend Engineer")
        self.assertEqual(position.organization, "Orbit")
        self.assertEqual(position.months, 41)

    def test_education_dates_are_excluded(self):
        titles = [p.title for p in extract.extract_positions(CV)]
        self.assertNotIn("BSc", titles)

    def test_ongoing_role_extends_to_today(self):
        positions = extract.extract_positions("Experience\nEngineer, Acme, 2024 - Present\n")
        self.assertTrue(positions[0].ongoing)
        self.assertGreater(positions[0].months, 12)

    def test_title_on_line_above_the_dates(self):
        cv = "Experience\n\nStaff Engineer, Orbit\nFeb 2020 - Jun 2023\n- Shipped things.\n"
        position = extract.extract_positions(cv)[0]
        self.assertEqual(position.title, "Staff Engineer")
        self.assertEqual(position.organization, "Orbit")

    def test_bullet_above_the_dates_is_not_used_as_a_title(self):
        cv = "Experience\n- Did a thing in 2019.\nEngineer\n2020 - 2021\n"
        self.assertEqual(extract.extract_positions(cv)[0].title, "Engineer")

    def test_overlapping_roles_counted_once(self):
        a = Position("A", None, extract.month_index(2020, 1), extract.month_index(2022, 12))
        b = Position("B", None, extract.month_index(2022, 1), extract.month_index(2023, 12))
        self.assertEqual(extract.merge_months([a, b]), 48)

    def test_gaps_are_not_counted(self):
        a = Position("A", None, extract.month_index(2015, 1), extract.month_index(2015, 12))
        b = Position("B", None, extract.month_index(2020, 1), extract.month_index(2020, 12))
        self.assertEqual(extract.merge_months([a, b]), 24)


class MetricsTests(unittest.TestCase):
    def test_counts_bullets_verbs_and_numbers(self):
        metrics = extract.extract_metrics(
            "Experience\n- Reduced costs by 30%.\n- Responsible for the newsletter.\n"
        )
        self.assertEqual(metrics.bullet_count, 2)
        self.assertEqual(metrics.quantified_bullets, 1)
        self.assertEqual(metrics.action_verb_bullets, 1)

    def test_detects_buzzwords(self):
        metrics = extract.extract_metrics("A results-driven team player and self-starter.")
        self.assertEqual(
            sorted(metrics.buzzwords), ["results-driven", "self-starter", "team player"]
        )


if __name__ == "__main__":
    unittest.main()

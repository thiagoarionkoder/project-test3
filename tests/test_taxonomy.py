import unittest

from cv_analyzer.taxonomy import default_taxonomy


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = default_taxonomy()

    def test_loads_every_category(self):
        self.assertGreater(len(self.taxonomy), 60)
        self.assertIn("languages", self.taxonomy.categories)

    def test_punctuated_names_match(self):
        hits = self.taxonomy.find("Strong C++, C# and Node.js, plus CI/CD experience.")
        self.assertEqual({"C++", "C#", "Node.js", "CI/CD"}, set(hits))

    def test_does_not_match_inside_words(self):
        hits = self.taxonomy.find("We use Gopher scripts and javadoc; no rusty code.")
        self.assertNotIn("Go", hits)
        self.assertNotIn("Java", hits)
        self.assertNotIn("Rust", hits)

    def test_aliases_resolve_to_canonical_name(self):
        hits = self.taxonomy.find("k8s and postgres and sklearn")
        self.assertEqual({"Kubernetes", "PostgreSQL", "scikit-learn"}, set(hits))

    def test_occurrences_are_reported_per_span(self):
        hits = self.taxonomy.find("Python, python3 and more Python")
        self.assertEqual(len(hits["Python"]), 3)

    def test_category_lookup(self):
        self.assertEqual(self.taxonomy.category_of("Docker"), "cloud_infra")
        with self.assertRaises(KeyError):
            self.taxonomy.category_of("COBOL")


if __name__ == "__main__":
    unittest.main()

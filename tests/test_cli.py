import io
import json
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from cv_analyzer.cli import main
from cv_analyzer.loaders import UnsupportedDocument, load_document

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
CV = str(SAMPLES / "alex_moreira.txt")
JOB = str(SAMPLES / "senior_backend_engineer.txt")

DOCX_XML = (
    '<?xml version="1.0"?><w:document xmlns:w="x"><w:body>'
    "<w:p><w:r><w:t>Ana Lima</w:t></w:r></w:p>"
    "<w:p><w:r><w:t>Python &amp; Docker</w:t></w:r></w:p>"
    "</w:body></w:document>"
)


def run(args):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(args)
    return code, buffer.getvalue()


class CliTests(unittest.TestCase):
    def test_analyze_prints_report(self):
        code, output = run(["analyze", CV])
        self.assertEqual(code, 0)
        self.assertIn("SCORE BREAKDOWN", output)
        self.assertIn("Alex Moreira", output)

    def test_analyze_json_is_valid(self):
        code, output = run(["analyze", CV, "--json"])
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertIn("skills", payload)

    def test_match_reports_gaps(self):
        code, output = run(["match", CV, JOB])
        self.assertEqual(code, 0)
        self.assertIn("JOB MATCH", output)
        self.assertIn("GAPS", output)

    def test_rank_orders_candidates(self):
        code, output = run(["rank", CV, str(SAMPLES / "priya_raman.txt")])
        self.assertEqual(code, 0)
        self.assertTrue(output.splitlines()[0].startswith("1. Alex Moreira"))

    def test_skills_lists_taxonomy(self):
        code, output = run(["skills"])
        self.assertEqual(code, 0)
        self.assertIn("Programming languages", output)

    def test_missing_file_returns_error_code(self):
        self.assertEqual(main(["analyze", "does-not-exist.txt"]), 1)


class LoaderTests(unittest.TestCase):
    def test_reads_docx_without_dependencies(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cv.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", DOCX_XML)
            text = load_document(path)
        self.assertIn("Ana Lima", text)
        self.assertIn("Python & Docker", text)

    def test_unknown_suffix_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cv.odt"
            path.write_text("x")
            with self.assertRaises(UnsupportedDocument):
                load_document(path)


if __name__ == "__main__":
    unittest.main()

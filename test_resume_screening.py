"""
Automated tests for the resume screening pipeline.

Covers skill extraction (including the word-boundary edge cases that
caused real bugs during development), section/degree/experience parsing,
PDF text extraction, relevance scoring, ranking/reporting, and a full
end-to-end run against the sample data.
"""

import csv
import os
import tempfile
import unittest

from resume_parser import (
    find_section, extract_degrees, estimate_years_of_experience, read_resume,
)
from skill_extractor import SkillExtractor
from scorer import compute_match_scores
from report import Candidate, guess_name, rank_candidates, write_ranking_csv
from main import run_screening

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
RESUMES_DIR = os.path.join(SAMPLE_DIR, "resumes")
JOB_PATH = os.path.join(SAMPLE_DIR, "job_description.txt")


class TestSkillExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = SkillExtractor(os.path.join(os.path.dirname(__file__), "skills.json"))

    def test_basic_skills_detected(self):
        text = "Experienced with Python, Django, and PostgreSQL."
        skills = self.extractor.extract_flat(text)
        self.assertIn("python", skills)
        self.assertIn("django", skills)
        self.assertIn("postgresql", skills)

    def test_java_does_not_match_inside_javascript(self):
        # This is the exact bug class found in the chatbot project: a short
        # skill name matching as a substring of an unrelated, longer word.
        skills = self.extractor.extract_flat("Experienced in JavaScript development.")
        self.assertNotIn("java", skills)
        self.assertIn("javascript", skills)

    def test_symbol_containing_skills_match(self):
        skills = self.extractor.extract_flat("Proficient in C++ and C#, with CI/CD experience.")
        self.assertIn("c++", skills)
        self.assertIn("c#", skills)
        self.assertIn("ci/cd", skills)

    def test_case_insensitive(self):
        skills = self.extractor.extract_flat("PYTHON and Docker and gIt")
        self.assertIn("python", skills)
        self.assertIn("docker", skills)
        self.assertIn("git", skills)

    def test_no_false_positive_on_unrelated_text(self):
        skills = self.extractor.extract_flat("I enjoy hiking and cooking on weekends.")
        self.assertEqual(skills, [])


class TestResumeParser(unittest.TestCase):
    def test_find_section_extracts_until_next_header(self):
        text = (
            "Summary\nA short bio.\n\n"
            "Education\nBachelor of Science in Computer Science, XYZ University\n\n"
            "Experience\nDid some jobs.\n"
        )
        education = find_section(text, "education")
        self.assertIn("Bachelor of Science", education)
        self.assertNotIn("Did some jobs", education)

    def test_find_section_missing_returns_empty(self):
        self.assertEqual(find_section("No sections here at all.", "education"), "")

    def test_extract_degrees(self):
        self.assertEqual(extract_degrees("Bachelor of Science in Computer Science"), ["Bachelor"])
        self.assertEqual(extract_degrees("Master of Business Administration (MBA)"), ["Master", "Mba"])
        self.assertEqual(extract_degrees("No degree info here"), [])

    def test_years_of_experience_explicit_mention(self):
        full_text = "Summary\n5 years of experience in backend development.\n"
        self.assertEqual(estimate_years_of_experience(full_text, ""), 5)

    def test_years_of_experience_falls_back_to_date_span_with_present(self):
        full_text = "Backend Developer, Acme Corp (2020 - Present)\nDid backend work."
        experience_text = "Backend Developer, Acme Corp (2020 - Present)\nDid backend work."
        years = estimate_years_of_experience(full_text, experience_text)
        self.assertIsNotNone(years)
        self.assertGreaterEqual(years, 4)  # 2020 to "present" (2026 in this project's test run)

    def test_years_of_experience_unknown_returns_none(self):
        self.assertIsNone(estimate_years_of_experience("No dates or years mentioned.", ""))

    def test_read_resume_txt(self):
        text = read_resume(os.path.join(RESUMES_DIR, "asha_rao.txt"))
        self.assertIn("Asha Rao", text)
        self.assertIn("Python", text)

    def test_read_resume_pdf(self):
        pdf_path = os.path.join(RESUMES_DIR, "karan_verma.pdf")
        text = read_resume(pdf_path)
        self.assertIn("Karan Verma", text)
        self.assertIn("Django", text)


class TestScorer(unittest.TestCase):
    def test_relevant_resume_scores_higher_than_irrelevant(self):
        job = "Looking for a Python backend developer with Django and REST API experience."
        relevant = "Backend developer skilled in Python, Django, and REST API design."
        irrelevant = "Marketing specialist experienced in social media and content writing."

        scores = compute_match_scores(job, [relevant, irrelevant])
        self.assertGreater(scores[0], scores[1])

    def test_identical_text_scores_highest(self):
        job = "Python Django REST API backend developer"
        scores = compute_match_scores(job, [job, "completely unrelated text about gardening"])
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], 90)


class TestReport(unittest.TestCase):
    def test_guess_name_from_first_line(self):
        text = "Jordan Lee\nSoftware Engineer\njordan@example.com"
        self.assertEqual(guess_name(text, "resume1.txt"), "Jordan Lee")

    def test_guess_name_falls_back_to_filename(self):
        text = "SKILLS AND EXPERIENCE\nPython, Django"
        self.assertEqual(guess_name(text, "jordan_lee.pdf"), "Jordan Lee")

    def test_rank_candidates_orders_by_score_descending(self):
        candidates = [
            Candidate(file_name="a.txt", name="A", score=10),
            Candidate(file_name="b.txt", name="B", score=80),
            Candidate(file_name="c.txt", name="C", score=45),
        ]
        ranked = rank_candidates(candidates)
        self.assertEqual([c.name for c in ranked], ["B", "C", "A"])

    def test_write_ranking_csv(self):
        candidates = [
            Candidate(file_name="a.txt", name="A", score=90.0, skills=["python"], degrees=["Bachelor"], years_experience=3),
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "ranking.csv")
            write_ranking_csv(candidates, csv_path)
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "A")
            self.assertEqual(rows[0]["match_score_percent"], "90.0")


class TestEndToEnd(unittest.TestCase):
    def test_run_screening_on_sample_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ranked = run_screening(JOB_PATH, RESUMES_DIR, output_dir=tmp_dir)

            names = [c.name for c in ranked]
            self.assertEqual(names[0], "Asha Rao")  # strongest Python/Django/AWS/Docker match
            self.assertEqual(names[-1], "Priya Sharma")  # unrelated marketing resume

            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "ranking.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "summary_report.txt")))

            scores = [c.score for c in ranked]
            self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()

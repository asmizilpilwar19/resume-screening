"""
CLI entry point: rank a folder of resumes against a job description.

Usage:
    python main.py --job sample_data/job_description.txt --resumes sample_data/resumes
"""

import argparse
import os

from resume_parser import read_resume, find_section, extract_degrees, estimate_years_of_experience
from skill_extractor import SkillExtractor
from scorer import compute_match_scores
from report import Candidate, guess_name, rank_candidates, write_ranking_csv, write_summary_report, format_ranking_table

RESUME_EXTENSIONS = (".pdf", ".txt")


def discover_resume_files(resumes_dir):
    return [
        os.path.join(resumes_dir, name)
        for name in sorted(os.listdir(resumes_dir))
        if name.lower().endswith(RESUME_EXTENSIONS)
    ]


def build_candidate(file_path, extractor):
    """Parse one resume file into a Candidate (score is filled in later)."""
    text = read_resume(file_path)
    education_text = find_section(text, "education")
    experience_text = find_section(text, "experience")

    return text, Candidate(
        file_name=os.path.basename(file_path),
        name=guess_name(text, file_path),
        score=0.0,  # placeholder, set by run_screening() once all texts are collected
        skills=extractor.extract_flat(text),
        degrees=extract_degrees(education_text),
        education_text=education_text,
        years_experience=estimate_years_of_experience(text, experience_text),
    )


def run_screening(job_description_path, resumes_dir, output_dir="output", skills_path="skills.json"):
    """
    Parse the job description and every resume in resumes_dir, score each
    resume against the job description, rank them, write ranking.csv and
    summary_report.txt into output_dir, and return the ranked candidates.
    """
    os.makedirs(output_dir, exist_ok=True)

    job_text = read_resume(job_description_path)
    resume_files = discover_resume_files(resumes_dir)
    if not resume_files:
        raise ValueError(f"No .pdf or .txt resumes found in {resumes_dir}")

    extractor = SkillExtractor(skills_path)
    resume_texts = []
    candidates = []
    for file_path in resume_files:
        text, candidate = build_candidate(file_path, extractor)
        resume_texts.append(text)
        candidates.append(candidate)

    scores = compute_match_scores(job_text, resume_texts)
    for candidate, score in zip(candidates, scores):
        candidate.score = score

    ranked = rank_candidates(candidates)
    write_ranking_csv(ranked, os.path.join(output_dir, "ranking.csv"))
    write_summary_report(ranked, os.path.join(output_dir, "summary_report.txt"))
    return ranked


def main():
    parser = argparse.ArgumentParser(description="Rank resumes against a job description.")
    parser.add_argument("--job", required=True, help="Path to the job description (.txt or .pdf)")
    parser.add_argument("--resumes", required=True, help="Folder of resumes (.txt or .pdf files)")
    parser.add_argument("--output", default="output", help="Folder to write ranking.csv and summary_report.txt into")
    parser.add_argument("--skills", default="skills.json", help="Path to the skill keyword dataset")
    args = parser.parse_args()

    ranked = run_screening(args.job, args.resumes, args.output, args.skills)

    print(format_ranking_table(ranked))
    print(f"\nWrote {args.output}/ranking.csv and {args.output}/summary_report.txt")


if __name__ == "__main__":
    main()

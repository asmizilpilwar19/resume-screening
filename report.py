"""
Candidate ranking and reporting: turns per-resume extraction results plus
a match score into a ranked list, a CSV, a console table, and a per
-candidate text summary.
"""

import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Candidate:
    file_name: str
    name: str
    score: float
    skills: List[str] = field(default_factory=list)
    degrees: List[str] = field(default_factory=list)
    education_text: str = ""
    years_experience: Optional[int] = None


def guess_name(text, file_name):
    """Use the resume's first line if it looks like a person's name, else fall back to the filename."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped if _looks_like_name(stripped) else _name_from_filename(file_name)
    return _name_from_filename(file_name)


# Common resume header words. A first line containing any of these is a
# section label ("SKILLS AND EXPERIENCE"), not a person's name, even though
# it otherwise looks name-shaped (short, alphabetic, no digits).
_HEADER_WORDS = {
    "skills", "experience", "education", "summary", "objective", "profile",
    "projects", "certifications", "certificates", "employment", "history",
    "academic", "background", "references", "contact", "technical",
    "professional", "work", "resume", "curriculum", "vitae",
}


def _looks_like_name(line):
    if len(line) > 40 or "@" in line or any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    if not (1 <= len(words) <= 4):
        return False
    if any(word.lower() in _HEADER_WORDS for word in words):
        return False
    return all(word.replace(".", "").isalpha() for word in words)


def _name_from_filename(file_name):
    stem = os.path.splitext(os.path.basename(file_name))[0]
    return stem.replace("_", " ").replace("-", " ").title()


def rank_candidates(candidates):
    """Highest match score first."""
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def format_ranking_table(candidates, top_skills_shown=5):
    name_width = max([len(c.name) for c in candidates] + [4]) + 2
    header = f"{'Rank':<5}{'Name':<{name_width}}{'Score %':<9}{'Years':<7}Top Skills"
    lines = [header, "-" * len(header)]
    for rank, c in enumerate(candidates, start=1):
        top_skills = ", ".join(c.skills[:top_skills_shown]) or "-"
        years = c.years_experience if c.years_experience is not None else "-"
        lines.append(f"{rank:<5}{c.name:<{name_width}}{c.score:<9}{years:<7}{top_skills}")
    return "\n".join(lines)


def write_ranking_csv(candidates, output_path):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "name", "file", "match_score_percent", "years_experience", "degrees", "top_skills"])
        for rank, c in enumerate(candidates, start=1):
            writer.writerow([
                rank, c.name, c.file_name, c.score,
                c.years_experience if c.years_experience is not None else "",
                "; ".join(c.degrees), "; ".join(c.skills),
            ])


def write_summary_report(candidates, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("CANDIDATE SUMMARY REPORT\n")
        f.write("=" * 60 + "\n\n")
        for rank, c in enumerate(candidates, start=1):
            f.write(f"Rank #{rank}: {c.name}  ({c.file_name})\n")
            f.write(f"Match score: {c.score}%\n")
            years = c.years_experience if c.years_experience is not None else "Not detected"
            f.write(f"Years of experience (estimated): {years}\n")
            f.write(f"Degree(s): {', '.join(c.degrees) if c.degrees else 'Not detected'}\n")
            f.write(f"Top skills: {', '.join(c.skills) if c.skills else 'None detected'}\n")
            if c.education_text:
                f.write(f"Education section (raw): {c.education_text}\n")
            f.write("\n" + "-" * 60 + "\n\n")

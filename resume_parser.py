"""
Resume ingestion: turns a .pdf or .txt resume file into plain text, and
pulls out the raw "Education" and "Experience" sections by looking for
their section headers.

No NLP happens here — this module only deals with getting readable text
out of a file and locating sections within it. See preprocessing.py and
skill_extractor.py for the NLP side.
"""

import re
from datetime import date

import pdfplumber

# Section headers we know how to recognize. Used both to find the section
# we want and to know where it ends (i.e. where the NEXT section starts).
SECTION_HEADERS = {
    "summary": ["summary", "profile", "objective"],
    "skills": ["skills", "technical skills", "key skills"],
    "education": ["education", "academic background", "education background"],
    "experience": ["experience", "work experience", "professional experience",
                    "employment history"],
    "projects": ["projects"],
    "certifications": ["certifications", "certificates"],
}


def read_resume(file_path):
    """Return the plain text of a resume, whether it's a .pdf or .txt file."""
    lower_path = str(file_path).lower()
    if lower_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    return extract_text_from_txt(file_path)


def extract_text_from_pdf(file_path):
    """Extract all readable text from a PDF, page by page."""
    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return "\n".join(pages_text)


def extract_text_from_txt(file_path):
    """Read a plain-text resume, tolerating files that aren't strict UTF-8."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


def _all_header_aliases():
    return [alias for aliases in SECTION_HEADERS.values() for alias in aliases]


def find_section(text, section_name):
    """
    Return the raw text under a named section (e.g. "education"), stopping
    at the next recognized section header or the end of the document.
    Returns "" if the section header isn't found.
    """
    target_aliases = set(SECTION_HEADERS.get(section_name, [section_name]))
    other_aliases = [a for a in _all_header_aliases() if a not in target_aliases]

    lines = text.splitlines()
    start_index = None
    for i, line in enumerate(lines):
        cleaned = line.strip().strip(":").lower()
        if cleaned in target_aliases:
            start_index = i + 1
            break

    if start_index is None:
        return ""

    collected = []
    for line in lines[start_index:]:
        cleaned = line.strip().strip(":").lower()
        if cleaned in other_aliases:
            break
        collected.append(line)

    return "\n".join(collected).strip()


# Degree keywords used to detect education level without needing a full
# NER model. Checked case-insensitively against the education section.
_DEGREE_PATTERNS = [
    r"\bph\.?d\b", r"\bdoctorate\b",
    r"\bm\.?tech\b", r"\bm\.?s\b", r"\bm\.?sc\b", r"\bmba\b", r"\bmaster(?:'s|s)?\b",
    r"\bb\.?tech\b", r"\bb\.?s\b", r"\bb\.?sc\b", r"\bb\.?a\b", r"\bbachelor(?:'s|s)?\b",
    r"\bassociate(?:'s|s)?\s+degree\b",
]
_DEGREE_REGEX = re.compile("|".join(_DEGREE_PATTERNS), re.IGNORECASE)

# Matches things like "3 years", "3+ years", "3-5 years".
_YEARS_REGEX = re.compile(r"(\d+)\+?\s*-?\s*(?:to\s*\d+\s*)?years?", re.IGNORECASE)


def extract_degrees(education_text):
    """Return the degree-type keywords found in an education section."""
    return sorted(set(match.group(0).strip().title() for match in _DEGREE_REGEX.finditer(education_text)))


def estimate_years_of_experience(full_text, experience_text):
    """
    Best-effort estimate of years of experience.

    Looks first for an explicit "X years" mention ANYWHERE in the resume
    (most reliable — this is usually how a candidate states it themselves,
    often in a Summary section rather than inside Experience). If there
    isn't one, falls back to the span between the earliest and latest
    4-digit year mentioned in the experience section. This is a heuristic,
    not a precise calculation — see the README's Limitations section.
    """
    explicit_matches = _YEARS_REGEX.findall(full_text)
    if explicit_matches:
        return max(int(n) for n in explicit_matches)

    # Treat "Present" / "Current" / "Ongoing" as today's year, since that's
    # by far the most common way an ongoing role is written in a resume.
    normalized = re.sub(r"\b(present|current|ongoing|till date|to date)\b",
                         str(date.today().year), experience_text, flags=re.IGNORECASE)

    full_years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", normalized)]
    if len(full_years) >= 2:
        return max(full_years) - min(full_years)
    return None

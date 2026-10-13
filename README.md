# Resume Screening AI
\run_demo.ps1

An internship Task 2 project: a tool that parses resumes (PDF or text),
extracts skills/education/experience, scores each resume against a job
description using TF-IDF + cosine similarity, and produces a ranked
candidate report.

## Objective

Given a job description and a folder of resumes, automatically:
- Extract each candidate's skills, education, and experience.
- Score how well each resume matches the job description.
- Rank candidates by that score.
- Produce a report explaining *why* each candidate scored the way they did.

## Architecture

```
Job description file (.txt/.pdf)        Resume files (.txt/.pdf)
            |                                      |
            v                                      v
      resume_parser.read_resume()  <----- same function reads both
            |
            |-- find_section()        -> raw "Education" / "Experience" text
            |-- extract_degrees()     -> degree keywords (Bachelor, Master, ...)
            |-- estimate_years_of_experience()
            |
            v
      skill_extractor.SkillExtractor   -> skills found, via skills.json
            |
            v
      preprocessing.preprocess()       -> clean / tokenize / destopword / lemmatize
            |
            v
      scorer.compute_match_scores()    -> TF-IDF + cosine similarity (0-100)
            |
            v
      report.rank_candidates()         -> sorted by score
            |
            |-- write_ranking_csv()        -> output/ranking.csv
            |-- write_summary_report()     -> output/summary_report.txt
            |-- format_ranking_table()     -> printed to the console
```

| File | Responsibility |
|---|---|
| `main.py` | CLI entry point: discovers resumes, runs the pipeline, writes output |
| `resume_parser.py` | PDF/text extraction, section-finding, degree/experience-year heuristics |
| `skill_extractor.py` | Keyword-based skill matching against `skills.json` |
| `preprocessing.py` | NLP cleanup (tokenize, remove stopwords, lemmatize) before TF-IDF |
| `scorer.py` | TF-IDF vectorization + cosine similarity scoring |
| `report.py` | `Candidate` model, ranking, CSV/text report writers |
| `skills.json` | The domain skill-keyword dataset |
| `sample_data/` | A sample job description and 4 sample resumes (3 `.txt`, 1 `.pdf`) |
| `output/` | Generated `ranking.csv` and `summary_report.txt` (committed as example deliverables) |
| `test_resume_screening.py` | Automated tests |

## Technologies used

- Python 3
- `pdfplumber` — PDF text extraction
- `nltk` — tokenization, stopword removal, lemmatization
- `scikit-learn` — TF-IDF vectorization and cosine similarity
- Standard library (`re`, `csv`, `json`, `argparse`, `dataclasses`) for
  everything else, including skill extraction and section parsing

A CLI was chosen over Flask/Streamlit (both allowed by the assignment)
because it's deterministic and easy to script/test end-to-end, and
because the ranking table/CSV/report are themselves the clearest "UI" for
this kind of batch comparison task.

## How the scoring algorithm works

1. **Preprocessing** (`preprocessing.py`): the job description and every
   resume are lowercased, stripped of punctuation, tokenized, had English
   stopwords removed, and lemmatized (e.g. "developing"/"developed" →
   "develop"). This means the comparison is based on *meaningful* words,
   not exact phrasing.
2. **Vectorization** (`scorer.py`): all the preprocessed documents (job
   description + every resume) are fit into one shared TF-IDF
   (Term Frequency–Inverse Document Frequency) vector space using
   `sklearn.feature_extraction.text.TfidfVectorizer`. TF-IDF weighs a word
   higher if it appears often in a document but rarely across the whole
   set — so generic words score low and distinctive, job-relevant words
   (like "django" or "postgresql") score high.
3. **Similarity** (`scorer.py`): `cosine_similarity` measures the angle
   between the job description's vector and each resume's vector. A score
   of 100 would mean identical wording; 0 means no shared meaningful
   vocabulary at all. The result is reported as a 0–100 "match score".
4. **Ranking** (`report.py`): candidates are sorted by that score,
   descending.

This is intentionally a classic, explainable IR (information retrieval)
technique rather than a black-box embedding model — every score can be
traced back to actual shared vocabulary between the resume and the job
description.

## How skill/education/experience extraction works

- **Skills** (`skill_extractor.py`): keyword matching against
  `skills.json` (organized into categories: programming languages, web,
  data/AI/ML, databases, cloud/DevOps, tools, soft skills). Each skill
  phrase is turned into a regex with explicit "not a letter/digit on
  either side" boundaries — plain substring search would wrongly match
  `"java"` inside `"javascript"`, or `"yo"`-style short tokens inside
  unrelated words. This boundary-safe check was verified by a real test
  case (`test_java_does_not_match_inside_javascript`).
- **Education** (`resume_parser.find_section()` + `extract_degrees()`):
  the raw text under an "Education" header is located by scanning for
  known section headers and taking everything until the next one. Degree
  keywords (Bachelor, Master, PhD, MBA, B.Tech, etc.) are then pulled out
  via regex. The raw section text is kept too, so a human reviewer can
  always see the original wording, not just the heuristic's conclusion.
- **Experience** (`resume_parser.estimate_years_of_experience()`): looks
  first for an explicit "X years of experience" statement anywhere in the
  resume (most reliable, and often stated in a Summary section rather
  than inside "Experience" itself). If there's no explicit statement, it
  falls back to the span between the earliest and latest 4-digit year
  mentioned in the Experience section, treating "Present"/"Current"/
  "Ongoing" as today's year. This is a heuristic — see Limitations.

## Setup & how to run

```bash
cd week2/resume-screening
pip install -r requirements.txt
python main.py --job sample_data/job_description.txt --resumes sample_data/resumes --output output
```

Or, to avoid retyping/pasting that long command (and the risk of a
terminal splitting it across lines if it wraps mid-paste), just run the
included script instead:

```powershell
.\run_demo.ps1        # PowerShell
./run_demo.sh          # bash / Git Bash
```

NLTK will automatically download the small data packages it needs
(`punkt_tab`, `stopwords`, `wordnet`, `omw-1.4`) the first time it runs,
if they aren't already present.

**Note on first run:** the very first time you `import numpy`/`scikit-
learn` after installing, Windows Defender scanning the new DLLs can make
it take 10-30 seconds before anything prints. That's normal — let it
finish rather than pressing Ctrl+C. Every run after that is fast (under
2 seconds).

Run against your own data:

```bash
python main.py --job path/to/job_description.txt --resumes path/to/resumes_folder --output output
```

- `--job` accepts a `.txt` or `.pdf` file.
- `--resumes` is a folder; every `.txt` and `.pdf` file inside it is
  treated as one candidate's resume.
- `--skills` (optional) points at a different skill dataset if you want
  to screen for a different domain than the default `skills.json`.

This writes `output/ranking.csv` and `output/summary_report.txt`, and
prints a ranking table to the console.

## Sample data & example output

`sample_data/` contains one job description (Backend Python Developer)
and four resumes deliberately chosen to span a range of relevance:

| Resume | Profile | Format |
|---|---|---|
| `asha_rao.txt` | Python/Django backend developer — strong match | .txt |
| `karan_verma.pdf` | Full-stack Python/Django developer — partial match | .pdf |
| `rahul_mehta.txt` | Java/Spring Boot backend developer — partial overlap (SQL, AWS, Docker, Git) | .txt |
| `priya_sharma.txt` | Marketing/content specialist — unrelated field | .txt |

Actual output from running the command above (also committed in
`output/`):

```
Rank Name          Score %  Years  Top Skills
---------------------------------------------
1    Asha Rao      52.4     3      agile, aws, ci/cd, communication, data analysis
2    Rahul Mehta   26.4     4      aws, docker, git, java, jenkins
3    Karan Verma   24.9     2      communication, css, django, docker, git
4    Priya Sharma  6.2      5      communication, excel, leadership, time management
```

This ordering matches intuition: the Python/Django candidate with the
most overlapping tools (agile, AWS, CI/CD, Docker, Git) ranks highest, the
Java candidate with partial tool overlap ranks second, a shorter
full-stack Python resume missing some of the job's specific tooling
mentions ranks third, and the unrelated marketing resume ranks lowest.

## Testing

`test_resume_screening.py` (run with `python -m unittest
test_resume_screening -v`) covers:

- **Skill extraction**: correct matches, case-insensitivity, symbol-
  containing skills (`C++`, `C#`, `CI/CD`), and — importantly — that
  `"java"` does **not** falsely match inside `"javascript"`.
- **Resume parsing**: section extraction stops at the right boundary,
  degree detection, years-of-experience estimation (both the explicit-
  mention path and the date-span-with-"Present" fallback), and reading
  both `.txt` and a real generated `.pdf` resume.
- **Scoring**: a relevant resume scores higher than an irrelevant one;
  near-identical text scores near 100.
- **Reporting**: name-guessing from the first line (and correctly
  rejecting a section header like "SKILLS AND EXPERIENCE" that looks
  name-shaped — a real bug caught during development), ranking order,
  and CSV output.
- **End-to-end**: running the full pipeline on the sample data produces
  the expected top/bottom candidates and writes both output files.

All 20 tests pass as of this project's last run (2026-10-05).

Two real bugs were caught and fixed by these tests during development:
1. `"java"` was briefly matching inside `"javascript"` before boundary-safe
   regexes were added to skill matching.
2. The name-guessing heuristic accepted `"SKILLS AND EXPERIENCE"` as a
   plausible name (it's short and all-alphabetic) until a header-word
   exclusion list was added.

## Limitations

- **Skill extraction is keyword-based**, not true NLU — a skill phrased
  unusually, abbreviated differently, or implied rather than named won't
  be detected. `skills.json` can be extended with more synonyms over time.
- **Years-of-experience is a heuristic**, not a precise calculation. It
  trusts an explicit "X years" statement if present; otherwise it
  estimates from the earliest-to-latest year mentioned, which can
  overstate experience if a resume lists an unrelated early year, or
  understate it if dates are formatted unusually.
- **Name detection** uses a simple "does the first line look like a
  name" heuristic plus a filename fallback — unusual resume layouts
  (e.g. a logo/header image as PDF text, or a name split across two
  lines) can fool it.
- **PDF extraction** depends on the PDF containing real text (not a
  scanned image with no OCR layer); `pdfplumber` can't read text from a
  flat image.
- **TF-IDF scoring** measures vocabulary overlap, not true semantic
  meaning — a resume that uses different-but-equivalent terminology from
  the job description (e.g. "backend services" vs. "server-side
  applications") may score lower than its actual fit would suggest.

## Evaluation criteria — where each is addressed

| Criterion | Where |
|---|---|
| Accuracy of skill extraction | `skill_extractor.py` + boundary-safety tests |
| Relevance of the ranking algorithm | `scorer.py` (TF-IDF + cosine similarity) + scoring tests |
| Interface clarity | `main.py`'s console table, plus `ranking.csv` / `summary_report.txt` |
| Handling of different resume formats | `resume_parser.py` supports both `.txt` and `.pdf`, tested against a real generated PDF |
| Code quality and documentation | Modular files (one responsibility each), docstrings, this README |

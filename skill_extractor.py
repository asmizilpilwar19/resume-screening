"""
Skill extraction via keyword matching against skills.json.

Deliberately NOT a machine-learning / NER model: the assignment allows
"keyword matching or NER", and keyword matching is transparent — every
match can be traced back to one entry in skills.json, which matters for
a tool whose job is to explain *why* a candidate scored the way they did.
"""

import json
import re


def load_skills(skills_path="skills.json"):
    with open(skills_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_pattern(skill):
    """
    A word-boundary-safe pattern for one skill phrase.

    Plain \\b boundaries misbehave on skills containing symbols (c++, c#,
    node.js, ci/cd), so boundaries are defined explicitly as "not a letter
    or digit on either side" instead. This also stops short skills from
    matching inside unrelated words (e.g. "java" must not match inside
    "javascript").
    """
    escaped = re.escape(skill.lower())
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


class SkillExtractor:
    def __init__(self, skills_path="skills.json"):
        self.skills_by_category = load_skills(skills_path)
        self._patterns = [
            (category, skill, _build_pattern(skill))
            for category, skills in self.skills_by_category.items()
            for skill in skills
        ]

    def extract(self, text):
        """Return {category: [matched skill names]} for skills found in text."""
        found = {}
        for category, skill, pattern in self._patterns:
            if pattern.search(text):
                found.setdefault(category, []).append(skill)
        return found

    def extract_flat(self, text):
        """Return a flat, alphabetically sorted list of all matched skills."""
        found = self.extract(text)
        return sorted({skill for skills in found.values() for skill in skills})

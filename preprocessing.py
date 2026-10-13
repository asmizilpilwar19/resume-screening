"""
Generic NLP preprocessing used before TF-IDF scoring (not used for skill
extraction, which needs the original text — see skill_extractor.py for why).

Pipeline: lowercase + strip punctuation -> tokenize -> remove stopwords ->
lemmatize -> rejoin into a single string ready for TfidfVectorizer.
"""

import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

_REQUIRED_NLTK_DATA = [
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("corpora/stopwords", "stopwords"),
    ("corpora/wordnet", "wordnet"),
    ("corpora/omw-1.4", "omw-1.4"),
]

for _resource_path, _package_name in _REQUIRED_NLTK_DATA:
    try:
        nltk.data.find(_resource_path)
    except LookupError:
        nltk.download(_package_name, quiet=True)

_STOPWORDS = set(stopwords.words("english"))
_LEMMATIZER = WordNetLemmatizer()


def clean_text(text):
    """Lowercase and strip everything except letters, digits, and spaces."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess(text):
    """Clean -> tokenize -> remove stopwords -> lemmatize -> rejoin."""
    cleaned = clean_text(text)
    tokens = word_tokenize(cleaned)
    tokens = [t for t in tokens if t not in _STOPWORDS and len(t) > 1]
    lemmas = [_LEMMATIZER.lemmatize(t) for t in tokens]
    return " ".join(lemmas)

"""
Relevance scoring: turns the job description and each resume into TF-IDF
vectors and scores every resume by its cosine similarity to the job
description. See the README's "How the scoring algorithm works" section
for the reasoning behind this choice.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from preprocessing import preprocess


def compute_match_scores(job_description_text, resume_texts):
    """
    Return a list of match scores (0-100, one decimal place), in the same
    order as resume_texts — how closely each resume matches the job
    description's wording, after shared preprocessing (lowercasing,
    stopword removal, lemmatization).
    """
    documents = [preprocess(job_description_text)] + [preprocess(t) for t in resume_texts]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)

    job_vector = tfidf_matrix[0:1]
    resume_vectors = tfidf_matrix[1:]

    similarities = cosine_similarity(job_vector, resume_vectors)[0]
    return [round(float(score) * 100, 1) for score in similarities]

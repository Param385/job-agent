"""
NLP utility functions for job description analysis.

These helpers work **without** an OpenAI key – they use simple heuristics and
optionally spaCy for keyword extraction.  They are called by
:class:`~src.jd_analyzer.extractor.JobDescriptionAnalyzer` when a fast,
offline analysis is required.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known tech skills – extend freely
# ---------------------------------------------------------------------------
TECH_SKILLS = {
    # Languages
    "python", "javascript", "typescript", "java", "go", "golang", "rust",
    "c++", "c#", "ruby", "php", "swift", "kotlin", "scala", "r",
    # Web / frontend
    "react", "vue", "angular", "nextjs", "html", "css", "tailwind",
    # Backend / frameworks
    "django", "flask", "fastapi", "spring", "express", "node", "nodejs",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite",
    "dynamodb", "elasticsearch", "cassandra",
    # Cloud / infra
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
    "ci/cd", "github actions", "jenkins", "ansible",
    # AI / ML
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "nlp", "llm", "openai", "langchain", "pandas", "numpy",
    # Tools
    "git", "linux", "bash", "rest", "graphql", "grpc", "kafka", "rabbitmq",
    "microservices", "agile", "scrum",
}

EXPERIENCE_PATTERNS = [
    (r"\b(\d+)\+?\s*years?\s+(?:of\s+)?experience\b", "years"),
    (r"\bsenior\b|\bsr\.\b|\blead\b|\bstaff\b|\bprincipal\b", "senior"),
    (r"\bjunior\b|\bjr\.\b|\bentry[- ]level\b|\bassociate\b|\bintern\b", "junior"),
    (r"\bmid[- ]?level\b|\bintermediate\b", "mid"),
]


def extract_skills_simple(text: str) -> List[str]:
    """Return a list of known tech skills found in *text* (case-insensitive).

    Uses word-boundary matching so that short skill names (e.g. ``"r"``,
    ``"go"``) are not matched as substrings of unrelated words.
    Does **not** require any external libraries.
    """
    lower = text.lower()
    found = []
    for skill in TECH_SKILLS:
        # Escape special regex chars (e.g. "c++", "c#")
        pattern = re.escape(skill)
        if re.search(r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])", lower):
            found.append(skill)
    return sorted(set(found))


def infer_experience_level(text: str) -> str:
    """Guess seniority level from job description text.

    Checks explicit seniority keywords first (senior/junior/mid), then
    falls back to extracting a years-of-experience number.

    Returns one of ``"junior"``, ``"mid"``, or ``"senior"``.
    """
    lower = text.lower()

    # Check explicit keywords first (highest priority)
    if re.search(r"\bsenior\b|\bsr\.\b|\blead\b|\bstaff\b|\bprincipal\b", lower):
        return "senior"
    if re.search(r"\bjunior\b|\bjr\.\b|\bentry[- ]level\b|\bassociate\b|\bintern\b", lower):
        return "junior"
    if re.search(r"\bmid[- ]?level\b|\bintermediate\b", lower):
        return "mid"

    # Fall back to years-of-experience extraction
    m = re.search(r"(\d+)\+?\s*years?", lower)
    if m:
        years = int(m.group(1))
        if years <= 2:
            return "junior"
        if years <= 5:
            return "mid"
        return "senior"

    return "mid"


def extract_keywords(text: str, top_n: int = 20) -> List[str]:
    """Extract the most frequent meaningful words from *text*.

    Uses spaCy when available for better noun/proper-noun extraction,
    otherwise falls back to a simple frequency approach.

    Parameters
    ----------
    text:
        Job description text.
    top_n:
        Maximum number of keywords to return.
    """
    try:
        return _extract_with_spacy(text, top_n)
    except Exception:
        return _extract_simple(text, top_n)


def _extract_with_spacy(text: str, top_n: int) -> List[str]:
    """spaCy-based extraction (noun chunks + named entities)."""
    import spacy  # noqa: PLC0415

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found – "
            "run: python -m spacy download en_core_web_sm"
        )
        raise

    doc = nlp(text[:10_000])  # spaCy has a default max length
    candidates: dict[str, int] = {}

    for chunk in doc.noun_chunks:
        word = chunk.text.lower().strip()
        if len(word) > 2:
            candidates[word] = candidates.get(word, 0) + 1

    for ent in doc.ents:
        word = ent.text.lower().strip()
        if len(word) > 2:
            candidates[word] = candidates.get(word, 0) + 1

    sorted_words = sorted(candidates, key=candidates.get, reverse=True)
    return sorted_words[:top_n]


def _extract_simple(text: str, top_n: int) -> List[str]:
    """Fallback keyword extractor using word frequency (no external deps)."""
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "will", "would", "can", "could", "should", "may", "we",
        "you", "they", "our", "your", "their", "this", "that", "it", "its",
        "not", "as", "if", "do", "does", "did", "so", "up", "out", "about",
        "into", "than", "more", "also", "we're", "you'll", "what", "how",
    }
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#\-]{1,}\b", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq, key=freq.get, reverse=True)
    return sorted_words[:top_n]

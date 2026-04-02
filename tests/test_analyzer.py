"""
Tests for the JD analyzer modules.
"""

import pytest

from src.jd_analyzer.nlp_utils import (
    extract_keywords,
    extract_skills_simple,
    infer_experience_level,
)
from src.jd_analyzer.extractor import JobDescriptionAnalyzer

SAMPLE_JD = """
We are looking for a Senior Python Developer to join our team.
Requirements:
- 5+ years of experience with Python
- Strong knowledge of Django and FastAPI
- Experience with PostgreSQL, Redis, and Docker
- Familiarity with AWS and Kubernetes
- Good understanding of REST APIs and microservices
- Nice to have: React, GraphQL
Benefits: remote work, health insurance, 401k, unlimited pto
"""


# ---------------------------------------------------------------------------
# NLP utilities
# ---------------------------------------------------------------------------

class TestExtractSkillsSimple:
    def test_finds_python(self):
        assert "python" in extract_skills_simple("We need a Python developer.")

    def test_finds_multiple_skills(self):
        skills = extract_skills_simple(SAMPLE_JD)
        assert "python" in skills
        assert "django" in skills
        assert "docker" in skills
        assert "postgresql" in skills

    def test_case_insensitive(self):
        assert "python" in extract_skills_simple("PYTHON DEVELOPER")

    def test_empty_text_returns_empty(self):
        assert extract_skills_simple("") == []

    def test_no_skills_text(self):
        assert extract_skills_simple("Hello world, I love cats.") == []


class TestInferExperienceLevel:
    def test_senior_from_title(self):
        assert infer_experience_level("Senior Python Developer") == "senior"

    def test_junior_from_text(self):
        assert infer_experience_level("entry-level position for juniors") == "junior"

    def test_years_senior(self):
        assert infer_experience_level("requires 7 years of experience") == "senior"

    def test_years_mid(self):
        assert infer_experience_level("3+ years of experience") == "mid"

    def test_years_junior(self):
        assert infer_experience_level("1 year of experience") == "junior"

    def test_default_mid(self):
        assert infer_experience_level("Developer wanted.") == "mid"


class TestExtractKeywords:
    def test_returns_list(self):
        result = extract_keywords(SAMPLE_JD)
        assert isinstance(result, list)

    def test_respects_top_n(self):
        result = extract_keywords(SAMPLE_JD, top_n=5)
        assert len(result) <= 5

    def test_empty_returns_empty(self):
        assert extract_keywords("") == []


# ---------------------------------------------------------------------------
# JobDescriptionAnalyzer
# ---------------------------------------------------------------------------

class TestJobDescriptionAnalyzer:
    def setup_method(self):
        # Disable AI so tests run without OpenAI key
        self.analyzer = JobDescriptionAnalyzer(use_ai=False)

    def test_analyze_returns_dict(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        assert isinstance(result, dict)

    def test_analyze_has_required_keys(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        for key in ("skills_required", "experience_level", "keywords", "years_required"):
            assert key in result, f"Missing key: {key}"

    def test_analyze_detects_senior(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        assert result["experience_level"] == "senior"

    def test_analyze_detects_skills(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        assert "python" in result["skills_required"]

    def test_analyze_detects_years(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        assert result["years_required"] == 5

    def test_analyze_extracts_benefits(self):
        result = self.analyzer.analyze(SAMPLE_JD)
        assert "remote" in result["benefits"] or "401k" in result["benefits"]

    def test_analyze_with_title_and_company(self):
        result = self.analyzer.analyze(SAMPLE_JD, title="Python Dev", company="Acme")
        assert result["title"] == "Python Dev"
        assert result["company"] == "Acme"

    def test_analyze_empty_text(self):
        result = self.analyzer.analyze("")
        assert isinstance(result, dict)
        assert result["skills_required"] == []

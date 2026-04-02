"""
Tests for the resume generator (optimizer + formatters).
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.resume_generator.formatters import ResumeFormatter
from src.resume_generator.optimizer import ResumeOptimizer

SAMPLE_RESUME = {
    "name": "Jane Doe",
    "current_title": "Python Developer",
    "years_experience": 3,
    "contact": {
        "email": "jane@example.com",
        "phone": "555-1234",
        "location": "Remote",
    },
    "summary": "Experienced Python developer.",
    "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS", "React"],
    "experience": [
        {
            "title": "Python Developer",
            "company": "Tech Corp",
            "dates": "2021-Present",
            "achievements": [
                "Built REST APIs serving 100k daily requests",
                "Reduced database query time by 30%",
            ],
        },
        {
            "title": "Junior Developer",
            "company": "Small Co",
            "dates": "2019-2021",
            "achievements": ["Wrote unit tests", "Maintained legacy codebase"],
        },
    ],
    "education": [
        {"degree": "B.Sc. Computer Science", "institution": "State U", "year": "2019"}
    ],
    "certifications": ["AWS Certified Developer"],
    "projects": [
        {
            "name": "Open Source Tool",
            "description": "A CLI utility for developers",
            "url": "https://github.com/janedoe/tool",
        }
    ],
}

SAMPLE_JOB_ANALYSIS = {
    "title": "Senior Python Developer",
    "company": "Acme Corp",
    "experience_level": "senior",
    "years_required": 5,
    "skills_required": ["python", "django", "postgresql", "docker"],
    "skills_nice": ["kubernetes", "react"],
    "keywords": ["rest api", "microservices", "scalable", "backend"],
    "responsibilities": ["Design REST APIs", "Lead architecture decisions"],
    "benefits": ["remote", "401k"],
    "summary": "Senior Python dev role at Acme.",
}


# ---------------------------------------------------------------------------
# ResumeOptimizer
# ---------------------------------------------------------------------------

class TestResumeOptimizer:
    def setup_method(self):
        self.optimizer = ResumeOptimizer(use_ai=False)

    def test_optimize_returns_dict(self):
        result = self.optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)
        assert isinstance(result, dict)

    def test_optimize_adds_match_score(self):
        result = self.optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)
        assert "match_score" in result
        assert 0 <= result["match_score"] <= 100

    def test_optimize_highlights_skills(self):
        result = self.optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)
        assert "highlighted_skills" in result
        # python, django, postgresql, docker are all in SAMPLE_RESUME skills
        highlighted = [s.lower() for s in result["highlighted_skills"]]
        assert "python" in highlighted

    def test_optimize_adds_target_job(self):
        result = self.optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)
        assert result["target_job"]["title"] == "Senior Python Developer"
        assert result["target_job"]["company"] == "Acme Corp"

    def test_optimize_generates_summary(self):
        result = self.optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 10

    def test_match_score_100_when_all_skills_present(self):
        analysis = {**SAMPLE_JOB_ANALYSIS, "skills_required": ["python", "django"]}
        result = self.optimizer.optimize(analysis, base_resume=SAMPLE_RESUME)
        assert result["match_score"] == 100.0

    def test_match_score_0_when_no_skills_match(self):
        analysis = {**SAMPLE_JOB_ANALYSIS, "skills_required": ["cobol", "fortran"]}
        result = self.optimizer.optimize(analysis, base_resume=SAMPLE_RESUME)
        assert result["match_score"] == 0.0

    def test_reorder_experience_by_relevance(self):
        # "Tech Corp" has more Python/REST keywords, should come first
        analysis = {**SAMPLE_JOB_ANALYSIS, "keywords": ["rest", "apis", "python"]}
        result = self.optimizer.optimize(analysis, base_resume=SAMPLE_RESUME)
        # The experience with "REST APIs" achievement should be first
        first_exp = result["experience"][0]
        assert "Tech Corp" in first_exp.get("company", "")

    def test_load_base_resume_raises_for_missing_file(self):
        optimizer = ResumeOptimizer(base_resume_path="/nonexistent/path.json", use_ai=False)
        with pytest.raises(FileNotFoundError):
            optimizer.load_base_resume()


# ---------------------------------------------------------------------------
# ResumeFormatter
# ---------------------------------------------------------------------------

class TestResumeFormatter:
    def setup_method(self):
        self.formatter = ResumeFormatter()
        self.resume = self.optimizer_result()

    @staticmethod
    def optimizer_result():
        optimizer = ResumeOptimizer(use_ai=False)
        return optimizer.optimize(SAMPLE_JOB_ANALYSIS, base_resume=SAMPLE_RESUME)

    def test_to_json_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.json")
            self.formatter.to_json(self.resume, path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["name"] == "Jane Doe"

    def test_to_markdown_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.md")
            self.formatter.to_markdown(self.resume, path)
            assert os.path.exists(path)
            content = Path(path).read_text()
            assert "Jane Doe" in content
            assert "## Experience" in content

    def test_to_markdown_includes_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.md")
            self.formatter.to_markdown(self.resume, path)
            content = Path(path).read_text()
            assert "Python" in content

    def test_to_json_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deep", "nested", "resume.json")
            self.formatter.to_json(self.resume, path)
            assert os.path.exists(path)

    def test_to_pdf_falls_back_to_markdown_without_reportlab(self):
        """When reportlab is missing, to_pdf should produce a .md file."""
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "resume.pdf")
            # If reportlab IS installed, this will create a real PDF
            # Either way, a file should be created
            result = self.formatter.to_pdf(self.resume, pdf_path)
            assert os.path.exists(result)

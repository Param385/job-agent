"""
Tests for the CLI commands.

Uses Typer's CliRunner so no real HTTP requests or AI calls are made.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_job_posting(title="Python Dev", company="Acme", url="https://example.com/job/1"):
    from src.scrapers.base_scraper import JobPosting
    return JobPosting(title=title, company=company, location="Remote", url=url, source="indeed")


# ---------------------------------------------------------------------------
# search command
# ---------------------------------------------------------------------------

class TestSearchCommand:
    @patch("src.cli.commands.search.IndeedScraper")
    @patch("src.cli.commands.search.init_db")
    @patch("src.cli.commands.search.save_job")
    def test_search_displays_results(self, mock_save, mock_init, MockScraper):
        mock_instance = MockScraper.return_value
        mock_instance.search_jobs.return_value = [
            make_job_posting("Python Dev", "Acme", "https://example.com/1")
        ]
        result = runner.invoke(app, ["search", "search", "--keywords", "Python", "--no-save"])
        assert result.exit_code == 0
        assert "Python Dev" in result.output

    @patch("src.cli.commands.search.IndeedScraper")
    @patch("src.cli.commands.search.init_db")
    def test_search_no_results(self, mock_init, MockScraper):
        mock_instance = MockScraper.return_value
        mock_instance.search_jobs.return_value = []
        result = runner.invoke(app, ["search", "search", "--keywords", "xyz123obscure"])
        assert result.exit_code != 0 or "No jobs found" in result.output


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------

class TestAnalyzeCommand:
    def test_analyze_with_text(self):
        result = runner.invoke(
            app,
            [
                "analyze", "analyze",
                "--text", "We need a senior Python developer with Django and PostgreSQL.",
                "--no-ai",
            ],
        )
        assert result.exit_code == 0
        # Should display experience level and skills
        assert "senior" in result.output.lower() or "Python" in result.output or "python" in result.output

    def test_analyze_missing_input(self):
        result = runner.invoke(app, ["analyze", "analyze", "--no-ai"])
        assert result.exit_code != 0 or "No job description" in result.output

    def test_analyze_with_file(self, tmp_path):
        jd_file = tmp_path / "jd.txt"
        jd_file.write_text("Senior Python developer needed. 5+ years experience with Django.")
        result = runner.invoke(
            app,
            ["analyze", "analyze", "--file", str(jd_file), "--no-ai"],
        )
        assert result.exit_code == 0

    def test_analyze_file_not_found(self):
        result = runner.invoke(
            app,
            ["analyze", "analyze", "--file", "/nonexistent/file.txt", "--no-ai"],
        )
        assert result.exit_code != 0 or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------

class TestGenerateCommand:
    @patch("src.cli.commands.generate.get_job_by_id")
    @patch("src.cli.commands.generate.init_db")
    def test_generate_job_not_found(self, mock_init, mock_get_job):
        mock_get_job.return_value = None
        result = runner.invoke(app, ["generate", "generate", "9999"])
        assert result.exit_code != 0 or "not found" in result.output.lower()

    @patch("src.cli.commands.generate.save_customized_resume")
    @patch("src.cli.commands.generate.ResumeFormatter")
    @patch("src.cli.commands.generate.ResumeOptimizer")
    @patch("src.cli.commands.generate.JobDescriptionAnalyzer")
    @patch("src.cli.commands.generate.get_job_by_id")
    @patch("src.cli.commands.generate.init_db")
    def test_generate_success(
        self,
        mock_init,
        mock_get_job,
        MockAnalyzer,
        MockOptimizer,
        MockFormatter,
        mock_save_resume,
        tmp_path,
    ):
        # Setup mock job
        mock_job = MagicMock()
        mock_job.id = 1
        mock_job.title = "Python Dev"
        mock_job.company = "Acme"
        mock_job.description = "Python developer needed."
        mock_job.analysis_json = None
        mock_get_job.return_value = mock_job

        # Setup mock analyzer
        mock_analyzer = MockAnalyzer.return_value
        mock_analyzer.analyze.return_value = {
            "title": "Python Dev",
            "company": "Acme",
            "skills_required": ["python"],
            "keywords": ["python"],
            "experience_level": "mid",
            "years_required": 3,
        }

        # Setup mock optimizer
        mock_opt = MockOptimizer.return_value
        mock_opt.optimize.return_value = {
            "name": "Jane",
            "skills": ["Python"],
            "match_score": 80.0,
            "highlighted_skills": ["Python"],
        }
        mock_opt.load_base_resume.return_value = {}

        # Setup mock formatter
        mock_fmt = MockFormatter.return_value
        mock_fmt.to_json.return_value = str(tmp_path / "resume.json")
        mock_fmt.to_markdown.return_value = str(tmp_path / "resume.md")
        mock_fmt.to_pdf.return_value = str(tmp_path / "resume.pdf")

        result = runner.invoke(
            app,
            ["generate", "generate", "1", "--output-dir", str(tmp_path), "--no-ai"],
        )
        # Check it ran without unexpected errors
        assert "80" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# stats command
# ---------------------------------------------------------------------------

class TestStatsCommand:
    @patch("src.cli.commands.stats.ApplicationAnalytics")
    @patch("src.cli.commands.stats.init_db")
    def test_stats_empty(self, mock_init, MockAnalytics):
        mock_instance = MockAnalytics.return_value
        mock_instance.get_summary.return_value = {
            "total": 0,
            "by_status": {},
            "response_rate": 0.0,
            "interview_rate": 0.0,
            "offer_rate": 0.0,
            "top_companies": [],
            "recent_activity": [],
        }
        result = runner.invoke(app, ["stats", "stats"])
        assert result.exit_code == 0
        assert "No applications" in result.output

    @patch("src.cli.commands.stats.ApplicationAnalytics")
    @patch("src.cli.commands.stats.init_db")
    def test_stats_with_data(self, mock_init, MockAnalytics):
        mock_instance = MockAnalytics.return_value
        mock_instance.get_summary.return_value = {
            "total": 10,
            "by_status": {"applied": 8, "interview": 2},
            "response_rate": 20.0,
            "interview_rate": 25.0,
            "offer_rate": 0.0,
            "top_companies": [{"company": "Acme", "applications": 3}],
            "recent_activity": [],
        }
        mock_instance.get_weekly_activity.return_value = []
        mock_instance.get_match_score_distribution.return_value = {
            "0-25": 1, "26-50": 3, "51-75": 4, "76-100": 2
        }
        result = runner.invoke(app, ["stats", "stats"])
        assert result.exit_code == 0
        assert "10" in result.output


# ---------------------------------------------------------------------------
# track command
# ---------------------------------------------------------------------------

class TestTrackCommand:
    @patch("src.cli.commands.track.get_applications")
    @patch("src.cli.commands.track.init_db")
    def test_track_list_empty(self, mock_init, mock_get_apps):
        mock_get_apps.return_value = []
        result = runner.invoke(app, ["track", "list"])
        assert result.exit_code == 0
        assert "No applications" in result.output

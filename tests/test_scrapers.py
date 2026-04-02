"""
Tests for the web scraper modules.

These tests use mocking so no real HTTP requests are made.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.scrapers.base_scraper import BaseScraper, JobPosting
from src.scrapers.indeed_scraper import IndeedScraper


# ---------------------------------------------------------------------------
# JobPosting dataclass
# ---------------------------------------------------------------------------

class TestJobPosting:
    def test_to_dict_basic(self):
        jp = JobPosting(
            title="Python Developer",
            company="Acme Corp",
            location="Remote",
            url="https://example.com/job/1",
            source="indeed",
        )
        d = jp.to_dict()
        assert d["title"] == "Python Developer"
        assert d["company"] == "Acme Corp"
        assert d["url"] == "https://example.com/job/1"
        assert d["source"] == "indeed"

    def test_to_dict_skills_joined(self):
        jp = JobPosting(
            title="Dev",
            company="Co",
            location="NYC",
            url="https://example.com",
            skills_required=["Python", "Django"],
        )
        assert jp.to_dict()["skills_required"] == "Python,Django"

    def test_to_dict_empty_skills(self):
        jp = JobPosting(title="Dev", company="Co", location="NYC", url="https://ex.com")
        assert jp.to_dict()["skills_required"] == ""


# ---------------------------------------------------------------------------
# BaseScraper helpers
# ---------------------------------------------------------------------------

class ConcreteScraper(BaseScraper):
    """Minimal concrete implementation for testing."""
    def search_jobs(self, keywords, location="", max_results=20):
        return []


class TestBaseScraperHelpers:
    def setup_method(self):
        self.scraper = ConcreteScraper()

    def test_clean_collapses_whitespace(self):
        assert self.scraper._clean("  hello   world  ") == "hello world"

    def test_infer_experience_level_senior(self):
        assert self.scraper._infer_experience_level("Senior Python Dev", "") == "senior"

    def test_infer_experience_level_junior(self):
        assert self.scraper._infer_experience_level("Junior Software Engineer", "") == "junior"

    def test_infer_experience_level_mid_default(self):
        assert self.scraper._infer_experience_level("Python Developer", "") == "mid"

    def test_infer_lead_is_senior(self):
        assert self.scraper._infer_experience_level("Lead Engineer", "") == "senior"


# ---------------------------------------------------------------------------
# IndeedScraper (mocked)
# ---------------------------------------------------------------------------

class TestIndeedScraper:
    def setup_method(self):
        self.scraper = IndeedScraper()

    @patch("src.scrapers.indeed_scraper.IndeedScraper._get")
    def test_search_returns_empty_on_failed_request(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        results = self.scraper.search_jobs("Python developer", "Remote")
        assert results == []

    @patch("src.scrapers.indeed_scraper.IndeedScraper._get")
    def test_search_returns_empty_when_no_cards(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>No jobs</p></body></html>"
        mock_get.return_value = mock_response
        results = self.scraper.search_jobs("Python developer")
        assert results == []

    @patch("src.scrapers.indeed_scraper.IndeedScraper._get")
    def test_search_parses_job_cards(self, mock_get):
        html = """
        <html><body>
        <div data-jk="abc123">
          <h2 class="jobTitle"><span>Python Developer</span></h2>
          <span data-testid="company-name">Acme Corp</span>
          <div data-testid="text-location">San Francisco, CA</div>
        </div>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        # Use max_results=1 so the scraper stops after the first page
        results = self.scraper.search_jobs("Python developer", max_results=1)
        assert len(results) == 1
        assert results[0].title == "Python Developer"
        assert results[0].company == "Acme Corp"
        assert results[0].source == "indeed"
        assert "abc123" in results[0].url

    def test_get_job_description_returns_empty_on_error(self):
        with patch.object(self.scraper, "_get", side_effect=Exception("error")):
            result = self.scraper.get_job_description("https://indeed.com/viewjob?jk=123")
            assert result == ""

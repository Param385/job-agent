"""
Indeed.com scraper.

Fetches job listings from Indeed by constructing the search URL and parsing
the returned HTML with BeautifulSoup.

Note on scraping
----------------
Indeed periodically updates its page structure.  If results stop working,
inspect the HTML response in ``DEBUG`` mode (set LOG_LEVEL=DEBUG in .env)
and update the CSS selectors in :meth:`_parse_job_cards`.

Ethical scraping
----------------
* We add a configurable delay between requests (default 2 s).
* We do **not** submit applications automatically.
* We respect robots.txt guidance: this scraper fetches *search result* pages
  only, not individual employer pages.
"""

import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

INDEED_BASE = "https://www.indeed.com"
INDEED_SEARCH = f"{INDEED_BASE}/jobs"


class IndeedScraper(BaseScraper):
    """Scrape job postings from Indeed.com."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search_jobs(
        self, keywords: str, location: str = "", max_results: int = 20
    ) -> List[JobPosting]:
        """Return up to *max_results* job postings from Indeed.

        Parameters
        ----------
        keywords:
            Job search query, e.g. ``"Python developer"``.
        location:
            City/state or ``"remote"``.
        max_results:
            Maximum number of listings to collect (paginates as needed).
        """
        jobs: List[JobPosting] = []
        start = 0
        page_size = 15  # Indeed shows ~15 results per page

        while len(jobs) < max_results:
            params = {
                "q": keywords,
                "l": location,
                "start": start,
                "limit": page_size,
            }
            try:
                response = self._get(INDEED_SEARCH, params=params)
            except Exception as exc:
                logger.error("Indeed request failed: %s", exc)
                break

            soup = BeautifulSoup(response.text, "lxml")
            cards = self._parse_job_cards(soup)
            if not cards:
                logger.debug("No more cards found – stopping pagination.")
                break

            jobs.extend(cards)
            start += page_size

        logger.info("IndeedScraper found %d jobs for %r in %r", len(jobs), keywords, location)
        return jobs[:max_results]

    def get_job_description(self, job_url: str) -> str:
        """Fetch the full description from a job's detail page.

        Returns an empty string on failure so callers don't need to
        handle exceptions.
        """
        try:
            response = self._get(job_url)
            soup = BeautifulSoup(response.text, "lxml")
            # Indeed wraps the description in a div with id="jobDescriptionText"
            container = soup.find("div", id="jobDescriptionText") or soup.find(
                "div", class_="jobsearch-jobDescriptionText"
            )
            if container:
                return self._clean(container.get_text(separator=" "))
        except Exception as exc:
            logger.warning("Could not fetch description from %s: %s", job_url, exc)
        return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_job_cards(self, soup: BeautifulSoup) -> List[JobPosting]:
        """Extract job cards from an Indeed search results page.

        Indeed renders results inside ``<div>`` elements with
        ``data-jk`` attributes (the job key).  The selectors here target
        the most common layout; adjust if Indeed changes its markup.
        """
        postings: List[JobPosting] = []

        # Primary container selector (as of 2024)
        cards = soup.find_all("div", attrs={"data-jk": True})
        if not cards:
            # Fallback: try the older card class
            cards = soup.find_all("div", class_="job_seen_beacon")

        for card in cards:
            try:
                posting = self._extract_card(card)
                if posting:
                    postings.append(posting)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Error parsing card: %s", exc)

        return postings

    def _extract_card(self, card) -> JobPosting | None:
        """Parse a single job card element into a :class:`JobPosting`."""
        # Title
        title_el = card.find("h2", class_=lambda c: c and "jobTitle" in c)
        if not title_el:
            return None
        title = self._clean(title_el.get_text())

        # Company name
        company_el = card.find(attrs={"data-testid": "company-name"}) or card.find(
            "span", class_=lambda c: c and "companyName" in c
        )
        company = self._clean(company_el.get_text()) if company_el else "Unknown"

        # Location
        loc_el = card.find(attrs={"data-testid": "text-location"}) or card.find(
            "div", class_=lambda c: c and "companyLocation" in c
        )
        location = self._clean(loc_el.get_text()) if loc_el else ""

        # URL – indeed job keys become /viewjob?jk=<key>
        job_key = card.get("data-jk", "")
        url = f"{INDEED_BASE}/viewjob?jk={job_key}" if job_key else ""
        if not url:
            link = card.find("a", href=True)
            url = INDEED_BASE + link["href"] if link else ""
        if not url:
            return None

        # Salary (optional)
        salary_el = card.find(attrs={"data-testid": "attribute_snippet_testid"}) or card.find(
            "div", class_=lambda c: c and "salary" in (c or "").lower()
        )
        salary = self._clean(salary_el.get_text()) if salary_el else ""

        return JobPosting(
            title=title,
            company=company,
            location=location,
            url=url,
            salary=salary,
            source="indeed",
            experience_level=self._infer_experience_level(title, ""),
        )

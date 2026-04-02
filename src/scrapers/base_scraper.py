"""
Abstract base class for all job-board scrapers.

Every concrete scraper must:
- Inherit from :class:`BaseScraper`
- Implement :meth:`search_jobs`
- Return a list of :class:`JobPosting` dataclass instances

Design principles
-----------------
* Rate-limiting  – mandatory delay between HTTP requests
* Retry logic    – exponential back-off via *tenacity*
* User-Agent     – configurable header to mimic a real browser
* Standardised output – all scrapers return identical :class:`JobPosting` objects
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import config

logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    """Standardised representation of a single job listing."""

    title: str
    company: str
    location: str
    url: str
    description: str = ""
    salary: str = ""
    job_type: str = ""          # full-time / part-time / contract / remote
    experience_level: str = ""  # junior / mid / senior
    source: str = ""            # indeed / linkedin / …
    skills_required: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "description": self.description,
            "salary": self.salary,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "source": self.source,
            "skills_required": ",".join(self.skills_required),
        }


class BaseScraper(ABC):
    """Base class with shared HTTP helpers and rate-limiting."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def search_jobs(self, keywords: str, location: str, max_results: int = 20) -> List[JobPosting]:
        """Scrape job listings for the given search query.

        Parameters
        ----------
        keywords:
            Space- or comma-separated job keywords (e.g. "Python developer").
        location:
            City, state, or "remote".
        max_results:
            Maximum number of listings to return.

        Returns
        -------
        list[JobPosting]
            Standardised job posting objects.
        """

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Block the calling thread until the minimum delay has elapsed."""
        elapsed = time.time() - self._last_request_time
        if elapsed < config.scraper_delay:
            time.sleep(config.scraper_delay - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """GET *url* with rate-limiting and automatic retries.

        Raises :class:`requests.HTTPError` for 4xx/5xx responses.
        """
        self._rate_limit()
        logger.debug("GET %s  params=%s", url, params)
        response = self.session.get(url, params=params, timeout=config.scraper_timeout)
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # Helpers shared across scrapers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(text: str) -> str:
        """Collapse whitespace and strip leading/trailing spaces."""
        return " ".join(text.split()).strip()

    @staticmethod
    def _infer_experience_level(title: str, description: str) -> str:
        """Guess seniority from job title / description text."""
        text = f"{title} {description}".lower()
        if any(w in text for w in ("senior", "sr.", "lead", "principal", "staff")):
            return "senior"
        if any(w in text for w in ("junior", "jr.", "entry", "associate", "intern")):
            return "junior"
        return "mid"

"""Scrapers package."""

from .base_scraper import BaseScraper, JobPosting
from .indeed_scraper import IndeedScraper

__all__ = ["BaseScraper", "JobPosting", "IndeedScraper"]

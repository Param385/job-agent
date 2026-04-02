"""
LinkedIn scraper (Selenium-based).

LinkedIn relies heavily on JavaScript rendering, so we use Selenium with a
headless Chrome/Chromium browser.  The ``webdriver-manager`` package
automatically downloads the correct ChromeDriver.

Prerequisites
-------------
* Google Chrome or Chromium must be installed on the machine.
* Install Python deps: ``pip install selenium webdriver-manager``

Usage
-----
::

    from src.scrapers.linkedin_scraper import LinkedInScraper
    scraper = LinkedInScraper()
    jobs = scraper.search_jobs("Python developer", "New York", max_results=10)
    scraper.close()

Note
----
LinkedIn's Terms of Service restrict automated access.  This scraper is
provided for educational purposes.  Use responsibly.
"""

import logging
import time
from typing import List, Optional

from src.config import config
from src.scrapers.base_scraper import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"


class LinkedInScraper(BaseScraper):
    """Scrape LinkedIn job postings using a headless Selenium browser."""

    def __init__(self, headless: bool = True) -> None:
        super().__init__()
        self._driver = None
        self._headless = headless

    # ------------------------------------------------------------------
    # Driver lifecycle
    # ------------------------------------------------------------------

    def _get_driver(self):
        """Lazy-initialise a headless Chrome WebDriver."""
        if self._driver is not None:
            return self._driver
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            if self._headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(f"user-agent={config.user_agent}")
            options.add_argument("--window-size=1920,1080")

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome WebDriver initialised (headless=%s)", self._headless)
        except Exception as exc:
            logger.error(
                "Failed to initialise Chrome WebDriver: %s\n"
                "Make sure Chrome/Chromium is installed and "
                "selenium + webdriver-manager are installed.",
                exc,
            )
            raise
        return self._driver

    def close(self) -> None:
        """Quit the Selenium browser and free resources."""
        if self._driver:
            self._driver.quit()
            self._driver = None
            logger.info("Chrome WebDriver closed.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search_jobs(
        self, keywords: str, location: str = "", max_results: int = 20
    ) -> List[JobPosting]:
        """Scrape LinkedIn job listings for the given search terms."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        jobs: List[JobPosting] = []
        driver = self._get_driver()

        params = f"keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
        url = f"{LINKEDIN_JOBS_URL}?{params}"

        try:
            driver.get(url)
            # Wait for job cards to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "base-card"))
            )
        except Exception as exc:
            logger.warning("LinkedIn page load timeout: %s", exc)
            return jobs

        # Scroll to load more results
        self._scroll_to_load(driver, max_results)

        cards = driver.find_elements(By.CLASS_NAME, "base-card")
        logger.info("Found %d LinkedIn cards", len(cards))

        for card in cards[:max_results]:
            posting = self._parse_card(card)
            if posting:
                jobs.append(posting)

        logger.info("LinkedInScraper returning %d jobs", len(jobs))
        return jobs

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _scroll_to_load(self, driver, target_count: int) -> None:
        """Scroll the page to trigger lazy-loading of more job cards."""
        scroll_attempts = 0
        max_scrolls = max(3, target_count // 10)
        while scroll_attempts < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(config.scraper_delay)
            scroll_attempts += 1

    def _parse_card(self, card) -> Optional[JobPosting]:
        """Extract job details from a LinkedIn base-card element."""
        try:
            from selenium.webdriver.common.by import By

            title_el = card.find_elements(By.CLASS_NAME, "base-search-card__title")
            company_el = card.find_elements(By.CLASS_NAME, "base-search-card__subtitle")
            location_el = card.find_elements(By.CLASS_NAME, "job-search-card__location")
            link_el = card.find_elements(By.TAG_NAME, "a")

            title = self._clean(title_el[0].text) if title_el else ""
            company = self._clean(company_el[0].text) if company_el else "Unknown"
            location = self._clean(location_el[0].text) if location_el else ""
            url = link_el[0].get_attribute("href") if link_el else ""

            if not title or not url:
                return None

            return JobPosting(
                title=title,
                company=company,
                location=location,
                url=url,
                source="linkedin",
                experience_level=self._infer_experience_level(title, ""),
            )
        except Exception as exc:
            logger.debug("Error parsing LinkedIn card: %s", exc)
            return None

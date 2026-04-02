"""
Configuration management for Job Agent.

This module reads settings from environment variables (or a .env file) and
exposes them through a typed Config dataclass so the rest of the application
never has to call os.environ directly.

Usage::

    from src.config import config
    print(config.openai_api_key)
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (silently ignored when it doesn't exist)
load_dotenv()

# ---------------------------------------------------------------------------
# Project-level paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class Config:
    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4"))
    openai_temperature: float = field(
        default_factory=lambda: float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///{DATA_DIR / 'jobs.db'}"
        )
    )

    # ------------------------------------------------------------------
    # Scraper settings
    # ------------------------------------------------------------------
    # Seconds to wait between requests (be respectful to job boards)
    scraper_delay: float = field(
        default_factory=lambda: float(os.getenv("SCRAPER_DELAY", "2.0"))
    )
    scraper_max_retries: int = field(
        default_factory=lambda: int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
    )
    scraper_timeout: int = field(
        default_factory=lambda: int(os.getenv("SCRAPER_TIMEOUT", "15"))
    )
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
    )

    # ------------------------------------------------------------------
    # Email (optional)
    # ------------------------------------------------------------------
    email_host: str = field(default_factory=lambda: os.getenv("EMAIL_HOST", "smtp.gmail.com"))
    email_port: int = field(default_factory=lambda: int(os.getenv("EMAIL_PORT", "587")))
    email_user: str = field(default_factory=lambda: os.getenv("EMAIL_USER", ""))
    email_password: str = field(default_factory=lambda: os.getenv("EMAIL_PASSWORD", ""))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", ""))
    notification_email: str = field(
        default_factory=lambda: os.getenv("NOTIFICATION_EMAIL", "")
    )

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------
    base_resume_path: str = field(
        default_factory=lambda: os.getenv(
            "BASE_RESUME_PATH", str(DATA_DIR / "base_resume.json")
        )
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


# Singleton instance used throughout the application
config = Config()

# Configure root logger once
logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

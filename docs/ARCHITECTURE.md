# System Architecture

## Overview

Job Agent is a modular Python application with six main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│    search | analyze | generate | track | stats             │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Core Business Logic                      │
│  Scrapers │ JD Analyzer │ Resume Generator │ App Manager  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     AI Engine Layer                         │
│              OpenAI GPT-4  │  spaCy NLP                    │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Database Layer                           │
│         SQLAlchemy ORM  │  SQLite (default)                │
└─────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### `src/config.py`
Single source of truth for all configuration. Reads `.env` via `python-dotenv`.
Exposes a singleton `config` object used throughout the app.

### `src/database/`
- `models.py` – SQLAlchemy ORM models: `Job`, `Application`, `CustomizedResume`
- `connection.py` – Engine, session factory, `init_db()`, `get_session()` context manager
- `operations.py` – CRUD operations for all models

### `src/scrapers/`
- `base_scraper.py` – Abstract `BaseScraper` with HTTP helpers (rate limiting, retries, user-agent)
- `indeed_scraper.py` – BeautifulSoup-based scraper for Indeed.com
- `linkedin_scraper.py` – Selenium-based scraper for LinkedIn

### `src/jd_analyzer/`
- `nlp_utils.py` – Offline NLP: skill extraction, experience level inference, keyword extraction
- `extractor.py` – `JobDescriptionAnalyzer` combines rule-based + GPT-4 analysis

### `src/resume_generator/`
- `optimizer.py` – `ResumeOptimizer` customises resume to match a job
- `formatters.py` – `ResumeFormatter` exports to JSON, Markdown, PDF

### `src/ai_engine/`
- `llm_client.py` – OpenAI API wrapper with retries and token logging

### `src/application_manager/`
- `tracker.py` – `ApplicationTracker` manages status transitions
- `analytics.py` – `ApplicationAnalytics` computes search statistics
- `email_notifier.py` – SMTP email notifications

### `src/cli/`
- `main.py` – Typer app combining all sub-commands
- `commands/` – One file per command: search, analyze, generate, track, stats

## Data Flow

```
User runs: job-agent search --keywords "Python developer"
                │
                ▼
        IndeedScraper.search_jobs()
                │
                ▼ (list of JobPosting objects)
        save_job() → Database (jobs table)
                │
                ▼
User runs: job-agent analyze --job-id 1
                │
                ▼
        JobDescriptionAnalyzer.analyze()
         ├── NLP utilities (offline)
         └── GPT-4 (if API key set)
                │
                ▼ (analysis dict)
        Update job.analysis_json in DB
                │
                ▼
User runs: job-agent generate 1
                │
                ▼
        ResumeOptimizer.optimize(analysis, base_resume)
         ├── Highlight matching skills
         ├── Reorder experience by relevance
         ├── Generate AI summary
         └── Compute match score
                │
                ▼ (customized resume dict)
        ResumeFormatter → JSON / Markdown / PDF
        save_customized_resume() → Database
```

## Database Schema

```sql
jobs (
    id INTEGER PRIMARY KEY,
    title TEXT, company TEXT, location TEXT, url TEXT UNIQUE,
    description TEXT, salary TEXT, job_type TEXT,
    experience_level TEXT, source TEXT, scraped_at DATETIME,
    skills_required TEXT, analysis_json TEXT
)

applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    status TEXT,  -- saved|applied|interview|offer|rejected
    applied_at DATETIME, notes TEXT,
    resume_used TEXT, match_score REAL,
    created_at DATETIME, updated_at DATETIME
)

customized_resumes (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    content_json TEXT, content_md TEXT,
    file_path TEXT, match_score REAL, created_at DATETIME
)
```

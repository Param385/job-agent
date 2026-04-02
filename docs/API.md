# API Reference

## Module: `src.config`

### `config` (singleton `Config`)
All configuration values as attributes.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `openai_api_key` | str | `""` | OpenAI API key |
| `openai_model` | str | `"gpt-4"` | GPT model |
| `database_url` | str | `sqlite:///./data/jobs.db` | SQLAlchemy DB URL |
| `scraper_delay` | float | `2.0` | Seconds between requests |
| `base_resume_path` | str | `data/base_resume.json` | Resume template path |

---

## Module: `src.scrapers`

### `class BaseScraper` (abstract)
```python
scraper._get(url, params=None) -> requests.Response
scraper._clean(text) -> str
scraper._infer_experience_level(title, description) -> str
```

### `class JobPosting`
```python
JobPosting(
    title: str, company: str, location: str, url: str,
    description: str = "", salary: str = "",
    job_type: str = "", experience_level: str = "",
    source: str = "", skills_required: list[str] = []
)
.to_dict() -> dict
```

### `class IndeedScraper(BaseScraper)`
```python
scraper.search_jobs(keywords, location="", max_results=20) -> list[JobPosting]
scraper.get_job_description(job_url) -> str
```

### `class LinkedInScraper(BaseScraper)`
```python
scraper.search_jobs(keywords, location="", max_results=20) -> list[JobPosting]
scraper.close()  # quit the Selenium WebDriver
```

---

## Module: `src.jd_analyzer`

### `class JobDescriptionAnalyzer`
```python
analyzer = JobDescriptionAnalyzer(use_ai=True)
result = analyzer.analyze(description, title="", company="") -> dict
```

**Returns:**
```json
{
  "title": "Senior Python Developer",
  "company": "Acme",
  "experience_level": "senior",
  "years_required": 5,
  "skills_required": ["python", "django"],
  "skills_nice": ["kubernetes"],
  "keywords": ["rest api", "microservices"],
  "responsibilities": ["Design APIs"],
  "benefits": ["remote", "401k"],
  "summary": "..."
}
```

### `nlp_utils` functions
```python
extract_skills_simple(text: str) -> list[str]
infer_experience_level(text: str) -> str  # "junior" | "mid" | "senior"
extract_keywords(text: str, top_n=20) -> list[str]
```

---

## Module: `src.resume_generator`

### `class ResumeOptimizer`
```python
optimizer = ResumeOptimizer(base_resume_path=None, use_ai=True)
resume_dict = optimizer.optimize(job_analysis, base_resume=None) -> dict
base = optimizer.load_base_resume() -> dict
```

### `class ResumeFormatter`
```python
formatter = ResumeFormatter()
formatter.to_json(resume, output_path) -> str   # returns abs path
formatter.to_markdown(resume, output_path) -> str
formatter.to_pdf(resume, output_path) -> str    # needs reportlab
```

---

## Module: `src.ai_engine`

### `class LLMClient`
```python
client = LLMClient(api_key=None, model=None)
client.complete(prompt, system_message=..., temperature=None, max_tokens=2048) -> str
client.chat(messages: list[dict]) -> str
client.generate_json(prompt) -> str  # instructs model to return JSON
```

---

## Module: `src.database`

### Connection
```python
from src.database.connection import init_db, get_session

init_db()  # create tables

with get_session() as session:
    # session is auto-committed on exit
```

### Operations
```python
from src.database.operations import *

save_job(job_data: dict) -> Job
get_jobs(limit, offset, source) -> list[Job]
get_job_by_id(job_id) -> Job | None
search_jobs(keyword) -> list[Job]

create_application(job_id, status, notes, match_score) -> Application
update_application_status(application_id, status, notes) -> Application | None
get_applications(status=None) -> list[Application]
get_application_stats() -> dict

save_customized_resume(job_id, content_json, content_md, file_path, match_score) -> CustomizedResume
get_resumes_for_job(job_id) -> list[CustomizedResume]
```

---

## Module: `src.application_manager`

### `class ApplicationTracker`
```python
tracker = ApplicationTracker()
tracker.save_job(job_id, notes, match_score) -> Application
tracker.mark_applied(application_id, notes) -> Application
tracker.mark_interview(application_id, notes) -> Application
tracker.mark_offer(application_id, notes) -> Application
tracker.mark_rejected(application_id, notes) -> Application
tracker.get_all(status=None) -> list[Application]
```

### `class ApplicationAnalytics`
```python
analytics = ApplicationAnalytics()
analytics.get_summary() -> dict
analytics.get_weekly_activity() -> list[dict]
analytics.get_match_score_distribution() -> dict
```

### `class EmailNotifier`
```python
notifier = EmailNotifier()
notifier.is_configured() -> bool
notifier.send(subject, body, html=False) -> bool
notifier.notify_new_jobs(jobs) -> bool
notifier.notify_status_change(job_title, company, old_status, new_status) -> bool
```

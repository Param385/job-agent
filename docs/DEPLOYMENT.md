# Deployment Guide

## Local Development

```bash
# Install
git clone https://github.com/Param385/job-agent.git
cd job-agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
job-agent --help
```

---

## Docker

### Build and run

```bash
# Build the image
docker compose build

# Search for jobs
docker compose run job-agent search --keywords "Python developer"

# Analyze a job (job ID from search above)
docker compose run job-agent analyze --job-id 1 --no-ai

# Generate a resume
docker compose run job-agent generate 1 --output-dir /app/output

# Interactive shell
docker compose run --entrypoint bash job-agent
```

### Environment variables in Docker

```bash
# Pass API key at runtime
OPENAI_API_KEY=sk-... docker compose run job-agent generate 1
```

Or add to `.env` (Docker Compose reads it automatically).

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_analyzer.py -v

# Run without AI (no API key needed)
pytest tests/ -v -k "not ai"
```

---

## CI/CD (GitHub Actions)

The included `.github/workflows/tests.yml` runs on every push and pull request:

- Tests on Python 3.10, 3.11, and 3.12
- Generates a coverage report
- Uploads to Codecov (optional)

To enable Codecov, add `CODECOV_TOKEN` to your repository secrets.

---

## Production Deployment

For a production setup, consider:

1. **Replace SQLite with PostgreSQL**:
   ```bash
   DATABASE_URL=postgresql://user:pass@host:5432/jobagent
   pip install psycopg2-binary
   ```

2. **Add a FastAPI web interface** (future enhancement):
   ```bash
   pip install fastapi uvicorn
   uvicorn src.web.app:app --host 0.0.0.0 --port 8000
   ```

3. **Schedule scraping with cron**:
   ```cron
   0 9 * * * /path/to/.venv/bin/job-agent search --keywords "Python developer" --location Remote
   ```

4. **Use a task queue for async AI processing** (Celery + Redis):
   ```bash
   pip install celery redis
   ```

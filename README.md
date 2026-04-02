# 🤖 Job Agent

> **AI-powered job application automation** – Find jobs, analyse JDs, generate tailored resumes, and track applications from the command line.

[![Tests](https://github.com/Param385/job-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Param385/job-agent/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Job Scraping** | Scrape Indeed (+ LinkedIn with Selenium) for live job listings |
| 🧠 **JD Analysis** | Extract skills, keywords, and requirements using GPT-4 + spaCy |
| 📄 **Resume Generator** | Auto-customise your resume to match each job description |
| 📊 **Application Tracker** | Track application status from saved → interview → offer |
| 📈 **Analytics** | See your response rate, interview rate, and top companies |
| 📧 **Email Notifications** | Get notified when new jobs are found (optional) |
| 🐳 **Docker Support** | Run everything in a container |

---

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Param385/job-agent.git
cd job-agent
pip install -r requirements.txt && pip install -e .

# 2. Configure (add your OpenAI key)
cp .env.example .env
nano .env

# 3. Edit your base resume
nano data/base_resume.json

# 4. Search for jobs
job-agent search --keywords "Python developer" --location "Remote"

# 5. Analyse a job description
job-agent analyze --job-id 1

# 6. Generate a tailored resume
job-agent generate 1

# 7. Track your application
job-agent track add 1
job-agent track update 1 --status applied
```

---

## 📖 Documentation

| Doc | Description |
|-----|-------------|
| [Tutorial](docs/TUTORIAL.md) | Step-by-step guide for beginners |
| [API Reference](docs/API.md) | Module and class documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design and data flow |
| [Deployment](docs/DEPLOYMENT.md) | Docker, CI/CD, production tips |

---

## 🏗 Project Structure

```
job-agent/
├── src/
│   ├── config.py                    # Configuration management
│   ├── database/                    # SQLAlchemy ORM + CRUD operations
│   ├── scrapers/                    # Indeed + LinkedIn scrapers
│   ├── jd_analyzer/                 # NLP + GPT-4 JD analysis
│   ├── resume_generator/            # Resume optimiser + PDF/MD export
│   ├── ai_engine/                   # OpenAI API wrapper
│   ├── application_manager/         # Tracker, analytics, email
│   └── cli/                         # Typer CLI commands
├── tests/                           # pytest test suite
├── data/
│   ├── base_resume.json             # ← Edit this with your info!
│   └── sample_job_posting.txt       # Example JD for testing
├── docs/                            # Documentation
├── .env.example                     # Config template
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 💻 CLI Commands

```bash
job-agent search --keywords "Python developer" --location "Remote" --max 20
job-agent analyze --job-id 1 --no-ai
job-agent generate 1 --format pdf
job-agent track list
job-agent track update 1 --status interview
job-agent stats --weekly
```

---

## 🛠 Tech Stack

- **Python 3.10+** – Core language
- **OpenAI GPT-4** – AI-powered analysis and resume writing
- **BeautifulSoup4 + Selenium** – Web scraping
- **SQLAlchemy + SQLite** – Data persistence
- **Typer + Rich** – Beautiful CLI
- **spaCy** – NLP keyword extraction
- **reportlab** – PDF generation
- **pytest** – Testing

---

## 🧪 Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 🐳 Docker

```bash
docker compose build
docker compose run job-agent search --keywords "Python developer"
```

---

## 📝 License

MIT License – see [LICENSE](LICENSE) for details.

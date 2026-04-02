# Job Agent – Step-by-Step Tutorial

This tutorial walks you through everything from installation to generating
your first AI-customised resume. Follow each step carefully. 

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or newer |
| pip | Latest |
| OpenAI API key | (for AI features) |
| Git | Any |

---

## Step 1 – Clone and Install

```bash
# Clone the repository
git clone https://github.com/Param385/job-agent.git
cd job-agent

# Create a virtual environment (keeps your system Python clean)
python -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
pip install -e .
```

---

## Step 2 – Configure Your Environment

```bash
# Copy the example config
cp .env.example .env

# Open .env in your editor and fill in your OpenAI API key
nano .env     # or: code .env / vim .env
```

Minimum `.env` content:

```ini
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4
```

> 💡 **Get an API key**: Sign up at [platform.openai.com](https://platform.openai.com),
> then go to **API Keys** and create a new secret key.

---

## Step 3 – Customise Your Base Resume

Edit `data/base_resume.json` with your real information:

```bash
nano data/base_resume.json
```

Key fields to fill in:
- `name` – your full name
- `contact` – email, phone, LinkedIn, GitHub
- `skills` – list all your technical skills
- `experience` – each job with achievements (quantify them!)
- `education` – degrees and institutions
- `certifications` – any relevant certs
- `projects` – portfolio projects with URLs

---

## Step 4 – Search for Jobs

```bash
# Search Indeed for Python developer roles
job-agent search --keywords "Python developer" --location "Remote" --max 20

# Search for specific role
job-agent search --keywords "Senior Django Engineer" --location "New York"

# Save results automatically (default behaviour)
job-agent search -k "Full Stack Developer" -l "San Francisco"
```

Results are saved to the local SQLite database (`data/jobs.db`).

---

## Step 5 – Analyse a Job Description

```bash
# Analyse a saved job by its database ID
job-agent analyze --job-id 1

# Analyse raw text directly
job-agent analyze --text "We need a Python developer with 5 years Django experience..."

# Analyse from a text file
job-agent analyze --file data/sample_job_posting.txt

# Save the analysis to a JSON file
job-agent analyze --job-id 1 --output output/analysis.json

# Run without OpenAI (rule-based only, faster but less accurate)
job-agent analyze --job-id 1 --no-ai
```

---

## Step 6 – Generate Your Customised Resume

```bash
# Generate resume for job #1 (all formats: JSON + Markdown + PDF)
job-agent generate 1

# Specific format only
job-agent generate 1 --format pdf
job-agent generate 1 --format markdown

# Custom output directory
job-agent generate 1 --output-dir ~/Desktop/resumes

# Run without AI (no API key needed, uses template)
job-agent generate 1 --no-ai

# Use a different base resume
job-agent generate 1 --resume path/to/other_resume.json
```

Generated files appear in the `output/` folder.

---

## Step 7 – Track Your Applications

```bash
# Add a job to your tracking list
job-agent track add 1

# List all tracked applications
job-agent track list

# Filter by status
job-agent track list --status applied

# Update application status
job-agent track update 1 --status applied
job-agent track update 1 --status interview --notes "Phone screen with HR on Monday"
job-agent track update 1 --status offer
job-agent track update 1 --status rejected --notes "They went with a more senior candidate"
```

Valid statuses: `saved` → `applied` → `interview` → `offer` / `rejected`

---

## Step 8 – View Statistics

```bash
# Overview dashboard
job-agent stats

# With weekly breakdown
job-agent stats --weekly
```

---

## Step 9 – Docker (Optional)

```bash
# Build the image
docker compose build

# Run a search
docker compose run job-agent search --keywords "Python developer"

# Open an interactive shell
docker compose run --entrypoint bash job-agent
```

---

## Troubleshooting

### "OpenAI API key not set"
Add `OPENAI_API_KEY=sk-...` to your `.env` file, or use `--no-ai` flag.

### "Base resume not found"
Edit `data/base_resume.json` with your information.

### "No jobs found"
- Try different keywords
- Indeed may block automated requests – try again later
- Check your internet connection

### Import errors
Make sure you ran `pip install -r requirements.txt` and `pip install -e .`

---

## Learning Path

Once you've got the basic agent working, explore these areas to level up:

1. **Read the source code** – start with `src/scrapers/base_scraper.py`
2. **Understand ORM models** – read `src/database/models.py`
3. **Study prompt engineering** – look at `src/jd_analyzer/extractor.py`
4. **Write more tests** – add edge cases to `tests/`
5. **Extend the CLI** – add a new command in `src/cli/commands/`
6. **Build a web UI** – add FastAPI routes exposing the same logic

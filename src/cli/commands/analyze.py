"""
analyze command – analyse a job description with NLP + AI.

Usage::

    job-agent analyze --job-id 3
    job-agent analyze --text "We are looking for a senior Python developer..."
    job-agent analyze --file path/to/jd.txt
"""

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.database.connection import init_db
from src.database.operations import get_job_by_id, save_job
from src.jd_analyzer.extractor import JobDescriptionAnalyzer

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Analyse a job description.")


@app.command()
def analyze(
    job_id: Optional[int] = typer.Option(None, "--job-id", "-j", help="ID of a saved job"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Raw job description text"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to a .txt JD file"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Use rule-based analysis only (no API key needed)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save JSON analysis to file"),
) -> None:
    """Extract skills, keywords, and requirements from a job description."""
    init_db()

    description, title, company = _load_description(job_id, text, file)
    if not description:
        console.print("[red]No job description provided. Use --job-id, --text, or --file.[/red]")
        raise typer.Exit(1)

    console.print("[bold cyan]🧠 Analysing job description...[/bold cyan]")
    analyzer = JobDescriptionAnalyzer(use_ai=not no_ai)
    result = analyzer.analyze(description, title=title, company=company)

    # Display results
    _display_analysis(result)

    # Optionally update DB
    if job_id:
        try:
            from src.database.connection import get_session
            with get_session() as session:
                job = get_job_by_id(job_id, session=session)
                if job:
                    job.analysis_json = json.dumps(result)
                    job.experience_level = result.get("experience_level", "")
                    job.skills_required = ",".join(result.get("skills_required", []))
            console.print(f"[green]✓ Analysis saved to job #{job_id}.[/green]")
        except Exception as exc:
            logger.warning("Could not update job #%d: %s", job_id, exc)

    # Save to output file
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]✓ Analysis saved to {output}[/green]")


def _load_description(
    job_id: Optional[int], text: Optional[str], file: Optional[Path]
) -> tuple[str, str, str]:
    """Return (description, title, company) from the specified source."""
    if job_id is not None:
        init_db()
        job = get_job_by_id(job_id)
        if not job:
            console.print(f"[red]Job #{job_id} not found in database.[/red]")
            raise typer.Exit(1)
        return job.description or "", job.title, job.company

    if file:
        if not file.exists():
            console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(1)
        return file.read_text(encoding="utf-8"), "", ""

    if text:
        return text, "", ""

    return "", "", ""


def _display_analysis(result: dict) -> None:
    """Pretty-print the analysis result."""
    # Summary panel
    summary = result.get("summary", "")
    if summary:
        console.print(Panel(summary, title="📋 Summary", border_style="cyan"))

    # Key info table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    table.add_row("Experience Level", result.get("experience_level", "—").capitalize())
    table.add_row("Years Required", str(result.get("years_required", 0)) or "—")
    console.print(table)

    # Skills
    skills = result.get("skills_required", [])
    if skills:
        console.print(f"\n[bold green]✅ Required Skills:[/bold green] {', '.join(skills)}")

    nice_skills = result.get("skills_nice", [])
    if nice_skills:
        console.print(f"[yellow]⭐ Nice-to-have:[/yellow] {', '.join(nice_skills)}")

    keywords = result.get("keywords", [])
    if keywords:
        console.print(f"[bold]🔑 Keywords:[/bold] {', '.join(keywords[:10])}")

    responsibilities = result.get("responsibilities", [])
    if responsibilities:
        console.print("\n[bold]📌 Key Responsibilities:[/bold]")
        for r in responsibilities[:5]:
            console.print(f"  • {r}")

    benefits = result.get("benefits", [])
    if benefits:
        console.print(f"\n[bold]🎁 Benefits:[/bold] {', '.join(benefits)}")

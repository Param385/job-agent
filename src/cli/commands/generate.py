"""
generate command – create a customised resume for a job.

Usage::

    job-agent generate --job-id 3
    job-agent generate --job-id 3 --format pdf
    job-agent generate --job-id 3 --no-ai --format markdown
"""

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from src.database.connection import init_db
from src.database.operations import get_job_by_id, save_customized_resume
from src.jd_analyzer.extractor import JobDescriptionAnalyzer
from src.resume_generator.formatters import ResumeFormatter
from src.resume_generator.optimizer import ResumeOptimizer

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Generate a customised resume for a job.")


@app.command()
def generate(
    job_id: int = typer.Argument(..., help="ID of the target job (from 'search' command)"),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Directory to save the resume"
    ),
    fmt: str = typer.Option(
        "all", "--format", "-f", help="Output format: json | markdown | pdf | all"
    ),
    no_ai: bool = typer.Option(
        False, "--no-ai", help="Skip AI enhancement (no OpenAI key needed)"
    ),
    resume_path: Optional[Path] = typer.Option(
        None, "--resume", "-r", help="Path to custom base resume JSON"
    ),
) -> None:
    """Generate a tailored resume for a specific job."""
    init_db()

    # Load the job from the database
    job = get_job_by_id(job_id)
    if not job:
        console.print(f"[red]Job #{job_id} not found. Run 'search' first.[/red]")
        raise typer.Exit(1)

    console.print(
        f"[bold cyan]🤖 Generating resume for:[/bold cyan] "
        f"[yellow]{job.title}[/yellow] at [yellow]{job.company}[/yellow]"
    )

    # Analyse the job description
    console.print("[dim]Analysing job description...[/dim]")
    analyzer = JobDescriptionAnalyzer(use_ai=not no_ai)

    if job.analysis_json:
        try:
            analysis = json.loads(job.analysis_json)
            console.print("[dim]Using cached analysis.[/dim]")
        except Exception:
            analysis = analyzer.analyze(job.description or "", job.title, job.company)
    else:
        analysis = analyzer.analyze(job.description or "", job.title, job.company)

    # Optimise the resume
    console.print("[dim]Customising resume...[/dim]")
    optimizer = ResumeOptimizer(
        base_resume_path=str(resume_path) if resume_path else None,
        use_ai=not no_ai,
    )
    try:
        optimized = optimizer.optimize(analysis)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    match_score = optimized.get("match_score", 0)
    console.print(f"[bold green]✓ Match score: {match_score:.0f}/100[/bold green]")

    # Export files
    formatter = ResumeFormatter()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
    base_name = f"resume_{safe_company}_{job_id}"

    exported: list[str] = []

    if fmt in ("json", "all"):
        path = formatter.to_json(optimized, str(output_dir / f"{base_name}.json"))
        exported.append(path)

    if fmt in ("markdown", "md", "all"):
        path = formatter.to_markdown(optimized, str(output_dir / f"{base_name}.md"))
        exported.append(path)

    if fmt in ("pdf", "all"):
        path = formatter.to_pdf(optimized, str(output_dir / f"{base_name}.pdf"))
        exported.append(path)

    # Save to database
    try:
        md_content = (output_dir / f"{base_name}.md").read_text() if (output_dir / f"{base_name}.md").exists() else ""
        save_customized_resume(
            job_id=job_id,
            content_json=optimized,
            content_md=md_content,
            file_path=exported[0] if exported else "",
            match_score=match_score,
        )
    except Exception as exc:
        logger.debug("Could not save resume to DB: %s", exc)

    # Summary
    console.print(Panel(
        "\n".join(f"📄 {p}" for p in exported),
        title="[bold green]Resume files created[/bold green]",
        border_style="green",
    ))

    if optimized.get("highlighted_skills"):
        skills = ", ".join(optimized["highlighted_skills"][:8])
        console.print(f"\n[bold]Highlighted skills:[/bold] {skills}")

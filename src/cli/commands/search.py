"""
search command – scrape job listings and store them in the database.

Usage::

    job-agent search --keywords "Python developer" --location "Remote" --source indeed
"""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.database.connection import init_db
from src.database.operations import save_job
from src.scrapers.indeed_scraper import IndeedScraper

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Search for jobs on job boards.")


@app.command()
def search(
    keywords: str = typer.Option(..., "--keywords", "-k", help="Job search keywords"),
    location: str = typer.Option("", "--location", "-l", help="City, state, or 'remote'"),
    source: str = typer.Option("indeed", "--source", "-s", help="Job board: indeed | linkedin"),
    max_results: int = typer.Option(20, "--max", "-n", help="Maximum results to fetch"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save results to database"),
) -> None:
    """Scrape job listings and optionally store them."""
    console.print(
        f"[bold cyan]🔍 Searching for[/bold cyan] [yellow]{keywords}[/yellow] "
        f"in [yellow]{location or 'anywhere'}[/yellow] on [yellow]{source}[/yellow]..."
    )

    init_db()
    jobs = _run_scraper(source, keywords, location, max_results)

    if not jobs:
        console.print("[red]No jobs found. Try different keywords or location.[/red]")
        raise typer.Exit(1)

    # Display results in a table
    table = Table(title=f"Job Results ({len(jobs)} found)", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Company", style="cyan")
    table.add_column("Location")
    table.add_column("Salary", style="green")
    table.add_column("URL", style="blue")

    for i, job in enumerate(jobs, 1):
        table.add_row(
            str(i),
            job.title,
            job.company,
            job.location or "—",
            job.salary or "—",
            job.url[:50] + "…" if len(job.url) > 50 else job.url,
        )
    console.print(table)

    # Save to database
    if save:
        saved_count = 0
        for job in jobs:
            try:
                save_job(job.to_dict())
                saved_count += 1
            except Exception as exc:
                logger.debug("Could not save job %r: %s", job.title, exc)
        console.print(f"[green]✓ Saved {saved_count} jobs to database.[/green]")


def _run_scraper(source: str, keywords: str, location: str, max_results: int):
    """Instantiate the correct scraper and run it."""
    if source == "linkedin":
        try:
            from src.scrapers.linkedin_scraper import LinkedInScraper
            scraper = LinkedInScraper()
            jobs = scraper.search_jobs(keywords, location, max_results)
            scraper.close()
            return jobs
        except Exception as exc:
            console.print(f"[red]LinkedIn scraper failed: {exc}[/red]")
            console.print("[yellow]Falling back to Indeed...[/yellow]")

    scraper = IndeedScraper()
    return scraper.search_jobs(keywords, location, max_results)

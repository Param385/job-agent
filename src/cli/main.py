"""
Job Agent CLI – entry point.

Run with::

    python -m src.cli.main --help
    # or after pip install -e .
    job-agent --help

Available commands
------------------
search   – Scrape job listings from job boards
analyze  – Analyse a job description with NLP + AI
generate – Create a customised resume for a job
track    – Track application statuses
stats    – View application analytics
"""

import typer
from rich.console import Console

from src.cli.commands import analyze, generate, search, stats, track

console = Console()

app = typer.Typer(
    name="job-agent",
    help=(
        "[bold cyan]Job Agent[/bold cyan] – AI-powered job application automation.\n\n"
        "Find jobs → Analyse JDs → Generate tailored resumes → Track applications."
    ),
    rich_markup_mode="rich",
    add_completion=False,
)

# Register sub-commands
app.add_typer(search.app, name="search", help="🔍 Scrape job listings from job boards")
app.add_typer(analyze.app, name="analyze", help="🧠 Analyse a job description")
app.add_typer(generate.app, name="generate", help="📄 Generate a tailored resume")
app.add_typer(track.app, name="track", help="📋 Track your applications")
app.add_typer(stats.app, name="stats", help="📊 View application statistics")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show help when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()

"""
stats command – display application analytics.

Usage::

    job-agent stats
    job-agent stats --weekly
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.application_manager.analytics import ApplicationAnalytics
from src.database.connection import init_db

console = Console()
app = typer.Typer(help="Show application statistics.")


@app.command()
def stats(
    weekly: bool = typer.Option(False, "--weekly", "-w", help="Show weekly activity breakdown"),
) -> None:
    """Display job application statistics and insights."""
    init_db()
    analytics = ApplicationAnalytics()
    summary = analytics.get_summary()

    if summary["total"] == 0:
        console.print("[yellow]No applications tracked yet. Run 'search' and 'track add' first.[/yellow]")
        return

    # Overview panel
    overview = (
        f"Total applications: [bold]{summary['total']}[/bold]\n"
        f"Response rate:  [cyan]{summary['response_rate']}%[/cyan]\n"
        f"Interview rate: [yellow]{summary['interview_rate']}%[/yellow]\n"
        f"Offer rate:     [green]{summary['offer_rate']}%[/green]"
    )
    console.print(Panel(overview, title="📊 Job Search Overview", border_style="cyan"))

    # Status breakdown table
    table = Table(title="Status Breakdown", show_header=True)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    status_colors = {
        "saved": "dim",
        "applied": "cyan",
        "interview": "yellow",
        "offer": "bold green",
        "rejected": "red",
    }
    for status, count in summary["by_status"].items():
        color = status_colors.get(status, "white")
        table.add_row(f"[{color}]{status.capitalize()}[/{color}]", str(count))
    console.print(table)

    # Top companies
    top = summary.get("top_companies", [])
    if top:
        console.print("\n[bold]🏢 Top Companies Applied To:[/bold]")
        for entry in top[:5]:
            console.print(f"  • {entry['company']}: {entry['applications']} application(s)")

    # Recent activity
    recent = summary.get("recent_activity", [])
    if recent:
        console.print("\n[bold]🕐 Recent Activity:[/bold]")
        for item in recent:
            console.print(
                f"  App #{item['id']} (Job #{item['job_id']}) → "
                f"[cyan]{item['status']}[/cyan]  {item['updated_at'][:10]}"
            )

    # Weekly breakdown
    if weekly:
        weekly_data = analytics.get_weekly_activity()
        if weekly_data:
            console.print("\n[bold]📅 Weekly Applications:[/bold]")
            w_table = Table()
            w_table.add_column("Week")
            w_table.add_column("Applications", justify="right")
            for row in weekly_data:
                w_table.add_row(row["week"], str(row["applications"]))
            console.print(w_table)

    # Match score distribution
    distribution = analytics.get_match_score_distribution()
    if any(distribution.values()):
        console.print("\n[bold]🎯 Match Score Distribution:[/bold]")
        for bucket, count in distribution.items():
            bar = "█" * count
            console.print(f"  {bucket:7s} | {bar} {count}")

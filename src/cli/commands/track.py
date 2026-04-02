"""
track command – view and update application history.

Usage::

    job-agent track list
    job-agent track list --status applied
    job-agent track update 5 --status interview --notes "Phone screen scheduled"
"""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.application_manager.tracker import VALID_STATUSES, ApplicationTracker
from src.database.connection import init_db
from src.database.operations import create_application, get_applications, get_job_by_id

console = Console()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Track job application history.")

STATUS_COLORS = {
    "saved": "dim",
    "applied": "cyan",
    "interview": "yellow",
    "offer": "bold green",
    "rejected": "red",
}


@app.command("list")
def list_applications(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List all tracked applications."""
    init_db()
    applications = get_applications(status=status)

    if not applications:
        msg = f"No applications with status '{status}'." if status else "No applications tracked yet."
        console.print(f"[yellow]{msg}[/yellow]")
        console.print("Tip: run [bold]job-agent search[/bold] first, then [bold]job-agent track add[/bold].")
        return

    table = Table(
        title=f"Applications ({len(applications)})",
        show_lines=True,
    )
    table.add_column("ID", style="dim", width=5)
    table.add_column("Job ID", width=7)
    table.add_column("Title", style="bold")
    table.add_column("Company", style="cyan")
    table.add_column("Status")
    table.add_column("Score", width=7)
    table.add_column("Applied At")
    table.add_column("Notes", max_width=30)

    from src.database.connection import get_session
    from src.database.models import Job

    with get_session() as session:
        job_map = {j.id: j for j in session.query(Job).all()}

        for a in applications:
            job = job_map.get(a.job_id)
            color = STATUS_COLORS.get(a.status, "white")
            table.add_row(
                str(a.id),
                str(a.job_id),
                job.title if job else "—",
                job.company if job else "—",
                f"[{color}]{a.status}[/{color}]",
                f"{a.match_score:.0f}%" if a.match_score else "—",
                a.applied_at.strftime("%Y-%m-%d") if a.applied_at else "—",
                (a.notes or "")[:30],
            )

    console.print(table)


@app.command("add")
def add_application(
    job_id: int = typer.Argument(..., help="Job ID to track"),
    notes: str = typer.Option("", "--notes", "-n", help="Notes"),
) -> None:
    """Add a job to your application tracker."""
    init_db()
    job = get_job_by_id(job_id)
    if not job:
        console.print(f"[red]Job #{job_id} not found.[/red]")
        raise typer.Exit(1)

    app_record = create_application(job_id=job_id, notes=notes)
    console.print(
        f"[green]✓ Added application #{app_record.id} for "
        f"'{job.title}' at '{job.company}'[/green]"
    )


@app.command("update")
def update_status(
    application_id: int = typer.Argument(..., help="Application ID"),
    status: str = typer.Option(..., "--status", "-s", help=f"New status: {VALID_STATUSES}"),
    notes: str = typer.Option("", "--notes", "-n", help="Optional notes"),
) -> None:
    """Update the status of an application."""
    init_db()
    tracker = ApplicationTracker()
    try:
        updated = tracker._transition(application_id, status, notes)
        if updated:
            console.print(
                f"[green]✓ Application #{application_id} updated to '{status}'.[/green]"
            )
        else:
            console.print(f"[red]Application #{application_id} not found.[/red]")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

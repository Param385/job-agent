"""
Application Tracker.

:class:`ApplicationTracker` provides a high-level API over the raw database
operations, adding business logic such as:

- Status transition validation
- Automatic applied_at timestamp setting
- Logging for audit trail
"""

import logging
from datetime import datetime
from typing import List, Optional

from src.database.connection import get_session, init_db
from src.database.models import Application, Job
from src.database.operations import (
    create_application,
    get_applications,
    get_job_by_id,
    update_application_status,
)

logger = logging.getLogger(__name__)

VALID_STATUSES = {"saved", "applied", "interview", "offer", "rejected"}

STATUS_TRANSITIONS = {
    "saved": {"applied", "rejected"},
    "applied": {"interview", "rejected"},
    "interview": {"offer", "rejected"},
    "offer": {"rejected"},
    "rejected": set(),
}


class ApplicationTracker:
    """Track job applications and their lifecycle."""

    def __init__(self) -> None:
        init_db()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def save_job(self, job_id: int, notes: str = "", match_score: float = 0.0) -> Application:
        """Add a job to the saved (wish-list) state."""
        app = create_application(
            job_id=job_id,
            status="saved",
            notes=notes,
            match_score=match_score,
        )
        logger.info("Saved job #%d to application tracker (app #%d)", job_id, app.id)
        return app

    def mark_applied(
        self,
        application_id: int,
        notes: str = "",
        resume_path: str = "",
    ) -> Optional[Application]:
        """Transition an application to 'applied' status."""
        return self._transition(application_id, "applied", notes)

    def mark_interview(
        self, application_id: int, notes: str = ""
    ) -> Optional[Application]:
        """Record that an interview was scheduled."""
        return self._transition(application_id, "interview", notes)

    def mark_offer(
        self, application_id: int, notes: str = ""
    ) -> Optional[Application]:
        """Record that an offer was received."""
        return self._transition(application_id, "offer", notes)

    def mark_rejected(
        self, application_id: int, notes: str = ""
    ) -> Optional[Application]:
        """Record a rejection."""
        return self._transition(application_id, "rejected", notes)

    def get_all(self, status: Optional[str] = None) -> List[Application]:
        """Return all tracked applications, optionally filtered by status."""
        return get_applications(status=status)

    def get_by_status(self, status: str) -> List[Application]:
        """Return applications with a specific status."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status!r}. Choose from {VALID_STATUSES}")
        return get_applications(status=status)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(
        self, application_id: int, new_status: str, notes: str
    ) -> Optional[Application]:
        with get_session() as session:
            app = session.query(Application).filter_by(id=application_id).first()
            if not app:
                logger.warning("Application #%d not found.", application_id)
                return None

            current = app.status
            allowed = STATUS_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Cannot transition from '{current}' to '{new_status}'. "
                    f"Allowed transitions: {allowed}"
                )

            app.status = new_status
            if notes:
                app.notes = (app.notes or "") + f"\n[{datetime.utcnow():%Y-%m-%d}] {notes}"
            if new_status == "applied" and not app.applied_at:
                app.applied_at = datetime.utcnow()

            logger.info(
                "Application #%d: %s → %s", application_id, current, new_status
            )
            return app

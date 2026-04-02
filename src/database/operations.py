"""
Database CRUD operations for Job Agent.

All public functions accept an optional *session* parameter so they can
participate in an existing transaction (useful in tests).  When *session* is
``None`` a new managed session is created automatically.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.connection import get_session
from src.database.models import Application, CustomizedResume, Job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def save_job(job_data: dict, session: Optional[Session] = None) -> Job:
    """Insert or update a job record.

    If a job with the same URL already exists it is updated in place and
    the existing row is returned.
    """
    def _save(s: Session) -> Job:
        existing = s.query(Job).filter_by(url=job_data["url"]).first()
        if existing:
            for key, value in job_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            logger.debug("Updated existing job: %s", job_data["url"])
            return existing
        job = Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)})
        s.add(job)
        s.flush()  # populate auto-generated id
        logger.debug("Saved new job: %s", job_data.get("title"))
        return job

    if session:
        return _save(session)
    with get_session() as s:
        return _save(s)


def get_jobs(
    limit: int = 50,
    offset: int = 0,
    source: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[Job]:
    """Return a list of jobs, optionally filtered by source."""
    def _get(s: Session) -> List[Job]:
        q = s.query(Job)
        if source:
            q = q.filter(Job.source == source)
        return q.order_by(Job.scraped_at.desc()).offset(offset).limit(limit).all()

    if session:
        return _get(session)
    with get_session() as s:
        return _get(s)


def get_job_by_id(job_id: int, session: Optional[Session] = None) -> Optional[Job]:
    """Fetch a single job by primary key."""
    def _get(s: Session) -> Optional[Job]:
        return s.query(Job).filter_by(id=job_id).first()

    if session:
        return _get(session)
    with get_session() as s:
        return _get(s)


def search_jobs(keyword: str, session: Optional[Session] = None) -> List[Job]:
    """Full-text search across job title, company, and description."""
    def _search(s: Session) -> List[Job]:
        pattern = f"%{keyword}%"
        return (
            s.query(Job)
            .filter(
                Job.title.ilike(pattern)
                | Job.company.ilike(pattern)
                | Job.description.ilike(pattern)
            )
            .all()
        )

    if session:
        return _search(session)
    with get_session() as s:
        return _search(s)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

def create_application(
    job_id: int,
    status: str = "saved",
    notes: str = "",
    match_score: float = 0.0,
    session: Optional[Session] = None,
) -> Application:
    """Record a new application for a job."""
    def _create(s: Session) -> Application:
        app = Application(
            job_id=job_id,
            status=status,
            notes=notes,
            match_score=match_score,
            applied_at=datetime.utcnow() if status == "applied" else None,
        )
        s.add(app)
        s.flush()
        return app

    if session:
        return _create(session)
    with get_session() as s:
        return _create(s)


def update_application_status(
    application_id: int,
    status: str,
    notes: str = "",
    session: Optional[Session] = None,
) -> Optional[Application]:
    """Update the status (and optionally notes) of an application."""
    def _update(s: Session) -> Optional[Application]:
        app = s.query(Application).filter_by(id=application_id).first()
        if not app:
            return None
        app.status = status
        if notes:
            app.notes = notes
        if status == "applied" and not app.applied_at:
            app.applied_at = datetime.utcnow()
        return app

    if session:
        return _update(session)
    with get_session() as s:
        return _update(s)


def get_applications(
    status: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[Application]:
    """Return applications, optionally filtered by status."""
    def _get(s: Session) -> List[Application]:
        q = s.query(Application)
        if status:
            q = q.filter(Application.status == status)
        return q.order_by(Application.created_at.desc()).all()

    if session:
        return _get(session)
    with get_session() as s:
        return _get(s)


def get_application_stats(session: Optional[Session] = None) -> dict:
    """Return a summary dict with counts by status."""
    def _stats(s: Session) -> dict:
        apps = s.query(Application).all()
        stats: dict = {
            "total": len(apps),
            "saved": 0,
            "applied": 0,
            "interview": 0,
            "offer": 0,
            "rejected": 0,
        }
        for app in apps:
            if app.status in stats:
                stats[app.status] += 1
        if stats["applied"] > 0:
            stats["interview_rate"] = round(stats["interview"] / stats["applied"] * 100, 1)
            stats["offer_rate"] = round(stats["offer"] / stats["applied"] * 100, 1)
        else:
            stats["interview_rate"] = 0.0
            stats["offer_rate"] = 0.0
        return stats

    if session:
        return _stats(session)
    with get_session() as s:
        return _stats(s)


# ---------------------------------------------------------------------------
# Customized Resumes
# ---------------------------------------------------------------------------

def save_customized_resume(
    job_id: int,
    content_json: dict,
    content_md: str = "",
    file_path: str = "",
    match_score: float = 0.0,
    session: Optional[Session] = None,
) -> CustomizedResume:
    """Store an AI-generated resume linked to a specific job."""
    def _save(s: Session) -> CustomizedResume:
        resume = CustomizedResume(
            job_id=job_id,
            content_json=json.dumps(content_json),
            content_md=content_md,
            file_path=file_path,
            match_score=match_score,
        )
        s.add(resume)
        s.flush()
        return resume

    if session:
        return _save(session)
    with get_session() as s:
        return _save(s)


def get_resumes_for_job(
    job_id: int, session: Optional[Session] = None
) -> List[CustomizedResume]:
    """Retrieve all customised resumes created for a job."""
    def _get(s: Session) -> List[CustomizedResume]:
        return (
            s.query(CustomizedResume)
            .filter_by(job_id=job_id)
            .order_by(CustomizedResume.created_at.desc())
            .all()
        )

    if session:
        return _get(session)
    with get_session() as s:
        return _get(s)

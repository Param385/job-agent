"""
Tests for the database layer.
"""

import json
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Job, Application, CustomizedResume
from src.database.operations import (
    save_job,
    get_jobs,
    get_job_by_id,
    search_jobs,
    create_application,
    get_applications,
    update_application_status,
    get_application_stats,
    save_customized_resume,
    get_resumes_for_job,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    """In-memory SQLite session for isolated tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


JOB_DATA = {
    "title": "Python Developer",
    "company": "Acme Corp",
    "location": "Remote",
    "url": "https://example.com/job/1",
    "description": "We need a Python developer with Django experience.",
    "salary": "$120k",
    "job_type": "full-time",
    "experience_level": "mid",
    "source": "indeed",
    "skills_required": "python,django",
}


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------

class TestJobOperations:
    def test_save_new_job(self, session):
        job = save_job(JOB_DATA, session=session)
        assert job.id is not None
        assert job.title == "Python Developer"
        assert job.company == "Acme Corp"

    def test_save_job_deduplicates_by_url(self, session):
        save_job(JOB_DATA, session=session)
        # Saving the same URL again should update, not insert
        updated_data = {**JOB_DATA, "title": "Senior Python Developer"}
        save_job(updated_data, session=session)
        jobs = session.query(Job).all()
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Python Developer"

    def test_get_jobs_returns_all(self, session):
        save_job(JOB_DATA, session=session)
        save_job({**JOB_DATA, "url": "https://example.com/job/2", "title": "Django Dev"}, session=session)
        jobs = get_jobs(session=session)
        assert len(jobs) == 2

    def test_get_jobs_limit(self, session):
        for i in range(5):
            save_job({**JOB_DATA, "url": f"https://example.com/job/{i}"}, session=session)
        jobs = get_jobs(limit=3, session=session)
        assert len(jobs) == 3

    def test_get_job_by_id(self, session):
        job = save_job(JOB_DATA, session=session)
        retrieved = get_job_by_id(job.id, session=session)
        assert retrieved is not None
        assert retrieved.title == job.title

    def test_get_job_by_id_missing(self, session):
        result = get_job_by_id(99999, session=session)
        assert result is None

    def test_search_jobs_by_title(self, session):
        save_job(JOB_DATA, session=session)
        save_job(
            {**JOB_DATA, "url": "https://example.com/job/2", "title": "Java Engineer",
             "description": "We need a Java engineer with Spring experience."},
            session=session,
        )
        results = search_jobs("Python", session=session)
        assert len(results) == 1
        assert results[0].title == "Python Developer"

    def test_search_jobs_by_company(self, session):
        save_job(JOB_DATA, session=session)
        results = search_jobs("Acme", session=session)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Application CRUD
# ---------------------------------------------------------------------------

class TestApplicationOperations:
    def test_create_application(self, session):
        job = save_job(JOB_DATA, session=session)
        app = create_application(job.id, status="saved", session=session)
        assert app.id is not None
        assert app.job_id == job.id
        assert app.status == "saved"

    def test_update_application_status(self, session):
        job = save_job(JOB_DATA, session=session)
        app = create_application(job.id, session=session)
        updated = update_application_status(app.id, "applied", session=session)
        assert updated.status == "applied"
        assert updated.applied_at is not None

    def test_update_nonexistent_application(self, session):
        result = update_application_status(99999, "applied", session=session)
        assert result is None

    def test_get_applications_all(self, session):
        job = save_job(JOB_DATA, session=session)
        create_application(job.id, status="saved", session=session)
        create_application(job.id, status="applied", session=session)
        apps = get_applications(session=session)
        assert len(apps) == 2

    def test_get_applications_filtered_by_status(self, session):
        job = save_job(JOB_DATA, session=session)
        create_application(job.id, status="saved", session=session)
        create_application(job.id, status="applied", session=session)
        saved = get_applications(status="saved", session=session)
        assert len(saved) == 1
        assert saved[0].status == "saved"

    def test_get_application_stats(self, session):
        job = save_job(JOB_DATA, session=session)
        create_application(job.id, status="applied", session=session)
        create_application(job.id, status="interview", session=session)
        stats = get_application_stats(session=session)
        assert stats["total"] == 2
        assert stats["applied"] == 1
        assert stats["interview"] == 1

    def test_application_stats_empty(self, session):
        stats = get_application_stats(session=session)
        assert stats["total"] == 0
        assert stats["interview_rate"] == 0.0


# ---------------------------------------------------------------------------
# Customized Resumes
# ---------------------------------------------------------------------------

class TestCustomizedResumeOperations:
    def test_save_and_retrieve_resume(self, session):
        job = save_job(JOB_DATA, session=session)
        content = {"name": "Jane", "skills": ["Python"]}
        resume = save_customized_resume(
            job_id=job.id,
            content_json=content,
            match_score=85.0,
            session=session,
        )
        assert resume.id is not None
        assert resume.match_score == 85.0

        retrieved = get_resumes_for_job(job.id, session=session)
        assert len(retrieved) == 1
        assert json.loads(retrieved[0].content_json)["name"] == "Jane"

    def test_get_resumes_empty(self, session):
        results = get_resumes_for_job(99999, session=session)
        assert results == []

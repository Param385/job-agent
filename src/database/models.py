"""
SQLAlchemy ORM models for Job Agent.

Tables
------
jobs            - Raw job listings collected by the scrapers
applications    - Tracks which jobs you have applied to and their status
customized_resumes - Stores AI-generated resume versions linked to a job
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base – all models inherit from this."""


class Job(Base):
    """A job listing scraped from a job board."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    url = Column(String(1024), unique=True, nullable=False)
    description = Column(Text)
    salary = Column(String(100))
    job_type = Column(String(50))          # full-time, part-time, contract …
    experience_level = Column(String(50))  # junior, mid, senior
    source = Column(String(50))            # indeed, linkedin …
    scraped_at = Column(DateTime, default=datetime.utcnow)
    # Denormalised skill list – stored as comma-separated string for simplicity
    skills_required = Column(Text)
    # AI-extracted analysis stored as JSON string
    analysis_json = Column(Text)

    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    resumes = relationship(
        "CustomizedResume", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r} company={self.company!r}>"


class Application(Base):
    """Records an application attempt for a particular job."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String(50), default="saved")  # saved, applied, interview, offer, rejected
    applied_at = Column(DateTime)
    notes = Column(Text)
    resume_used = Column(String(255))  # file path of the resume submitted
    match_score = Column(Float)        # 0-100 relevance score
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status={self.status!r}>"


class CustomizedResume(Base):
    """An AI-customised resume generated for a specific job."""

    __tablename__ = "customized_resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    content_json = Column(Text, nullable=False)   # full resume as JSON string
    content_md = Column(Text)                      # Markdown version
    file_path = Column(String(255))                # path to exported PDF/MD file
    match_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<CustomizedResume id={self.id} job_id={self.job_id}>"

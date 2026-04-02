"""
Application Analytics.

Computes statistics and insights from the application history.
"""

import logging
from collections import Counter
from typing import Any

from src.database.connection import get_session, init_db
from src.database.models import Application, Job

logger = logging.getLogger(__name__)


class ApplicationAnalytics:
    """Generate statistics and insights about your job search."""

    def __init__(self) -> None:
        init_db()

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all applications."""
        with get_session() as session:
            apps = session.query(Application).all()

            if not apps:
                return {
                    "total": 0,
                    "by_status": {},
                    "response_rate": 0.0,
                    "interview_rate": 0.0,
                    "offer_rate": 0.0,
                    "top_companies": [],
                    "recent_activity": [],
                }

            by_status = Counter(a.status for a in apps)
            total = len(apps)
            applied = by_status.get("applied", 0)
            interviews = by_status.get("interview", 0)
            offers = by_status.get("offer", 0)
            responded = interviews + offers + by_status.get("rejected", 0)

            # Fetch linked job company names
            job_ids = [a.job_id for a in apps]
            jobs = session.query(Job).filter(Job.id.in_(job_ids)).all()
            company_map = {j.id: j.company for j in jobs}
            companies = [company_map.get(a.job_id, "Unknown") for a in apps]
            top_companies = Counter(companies).most_common(5)

            # Recent activity (last 5 status changes)
            recent = sorted(apps, key=lambda a: a.updated_at or a.created_at, reverse=True)[:5]
            recent_activity = [
                {
                    "id": a.id,
                    "job_id": a.job_id,
                    "status": a.status,
                    "updated_at": str(a.updated_at or a.created_at),
                }
                for a in recent
            ]

            return {
                "total": total,
                "by_status": dict(by_status),
                "response_rate": round(responded / total * 100, 1) if total else 0.0,
                "interview_rate": round(interviews / applied * 100, 1) if applied else 0.0,
                "offer_rate": round(offers / applied * 100, 1) if applied else 0.0,
                "top_companies": [{"company": c, "applications": n} for c, n in top_companies],
                "recent_activity": recent_activity,
            }

    def get_weekly_activity(self) -> list[dict]:
        """Return application counts grouped by week."""
        from collections import defaultdict
        from datetime import timezone

        with get_session() as session:
            apps = session.query(Application).filter(
                Application.applied_at.isnot(None)
            ).all()

            weekly: dict[str, int] = defaultdict(int)
            for app in apps:
                week = app.applied_at.strftime("%Y-W%W")
                weekly[week] += 1

            return [
                {"week": week, "applications": count}
                for week, count in sorted(weekly.items())
            ]

    def get_match_score_distribution(self) -> dict[str, int]:
        """Bucket match scores into ranges."""
        with get_session() as session:
            apps = session.query(Application).filter(
                Application.match_score.isnot(None)
            ).all()

            buckets = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
            for app in apps:
                score = app.match_score or 0
                if score <= 25:
                    buckets["0-25"] += 1
                elif score <= 50:
                    buckets["26-50"] += 1
                elif score <= 75:
                    buckets["51-75"] += 1
                else:
                    buckets["76-100"] += 1
            return buckets

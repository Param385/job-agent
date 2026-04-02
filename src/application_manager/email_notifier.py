"""
Email Notifier.

Sends email notifications for application status changes using the standard
library's :mod:`smtplib` with STARTTLS encryption.

Configuration (add to .env)::

    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=you@gmail.com
    EMAIL_PASSWORD=your-app-password
    EMAIL_FROM=you@gmail.com
    NOTIFICATION_EMAIL=you@gmail.com

Gmail note
----------
Use an **App Password** (not your main password) when 2FA is enabled.
Go to: Google Account → Security → App Passwords.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.config import config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications about job application events.

    Parameters
    ----------
    host, port, user, password, from_addr, to_addr:
        Override config values – useful for testing.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addr: Optional[str] = None,
    ) -> None:
        self.host = host or config.email_host
        self.port = port or config.email_port
        self.user = user or config.email_user
        self.password = password or config.email_password
        self.from_addr = from_addr or config.email_from or self.user
        self.to_addr = to_addr or config.notification_email or self.user

    def is_configured(self) -> bool:
        """Return True only if all required credentials are set."""
        return bool(self.user and self.password and self.to_addr)

    def send(self, subject: str, body: str, html: bool = False) -> bool:
        """Send an email.

        Returns ``True`` on success, ``False`` on any error (errors are
        logged but not re-raised so the main workflow is not interrupted).
        """
        if not self.is_configured():
            logger.warning(
                "Email not configured – skipping notification. "
                "Add EMAIL_USER, EMAIL_PASSWORD, NOTIFICATION_EMAIL to .env."
            )
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.from_addr, [self.to_addr], msg.as_string())
            logger.info("Email sent: %s → %s", subject, self.to_addr)
            return True
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Pre-built notification templates
    # ------------------------------------------------------------------

    def notify_new_jobs(self, jobs: list[dict]) -> bool:
        """Send a digest of newly scraped jobs."""
        lines = [f"Found {len(jobs)} new job(s):\n"]
        for job in jobs[:20]:
            lines.append(
                f"• {job.get('title', '')} at {job.get('company', '')} – {job.get('url', '')}"
            )
        return self.send("Job Agent: New jobs found", "\n".join(lines))

    def notify_status_change(
        self, job_title: str, company: str, old_status: str, new_status: str
    ) -> bool:
        """Notify about a status transition."""
        subject = f"Application update: {job_title} at {company} → {new_status}"
        body = (
            f"Your application for **{job_title}** at **{company}** "
            f"changed from '{old_status}' to '{new_status}'."
        )
        return self.send(subject, body)

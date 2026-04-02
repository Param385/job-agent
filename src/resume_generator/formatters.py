"""
Resume formatters – export customised resumes to JSON, Markdown, and PDF.

Usage::

    from src.resume_generator.formatters import ResumeFormatter
    formatter = ResumeFormatter()

    formatter.to_json(resume, "output/resume.json")
    formatter.to_markdown(resume, "output/resume.md")
    formatter.to_pdf(resume, "output/resume.pdf")   # requires reportlab
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ResumeFormatter:
    """Export a resume dict to multiple file formats."""

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def to_json(self, resume: dict[str, Any], output_path: str) -> str:
        """Write the resume as a pretty-printed JSON file.

        Returns the absolute path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(resume, f, indent=2, ensure_ascii=False)
        logger.info("Resume saved as JSON: %s", path)
        return str(path.resolve())

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    def to_markdown(self, resume: dict[str, Any], output_path: str) -> str:
        """Write the resume as a Markdown file.

        Returns the absolute path of the written file.
        """
        md = self._build_markdown(resume)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(md)
        logger.info("Resume saved as Markdown: %s", path)
        return str(path.resolve())

    def _build_markdown(self, resume: dict[str, Any]) -> str:
        lines: list[str] = []

        # Header
        name = resume.get("name", "Your Name")
        lines.append(f"# {name}\n")

        contact = resume.get("contact", {})
        contact_parts = [
            contact.get("email", ""),
            contact.get("phone", ""),
            contact.get("linkedin", ""),
            contact.get("github", ""),
            contact.get("location", ""),
        ]
        lines.append(" | ".join(p for p in contact_parts if p))
        lines.append("")

        # Summary
        summary = resume.get("summary", "")
        if summary:
            lines.append("## Professional Summary\n")
            lines.append(summary)
            lines.append("")

        # Highlighted skills
        highlighted = resume.get("highlighted_skills", [])
        all_skills = resume.get("skills", [])
        display_skills = highlighted if highlighted else all_skills
        if display_skills:
            lines.append("## Skills\n")
            lines.append(", ".join(display_skills))
            lines.append("")

        # Experience
        experience = resume.get("experience", [])
        if experience:
            lines.append("## Experience\n")
            for job in experience:
                company = job.get("company", "")
                title = job.get("title", "")
                dates = job.get("dates", "")
                lines.append(f"### {title} – {company}")
                if dates:
                    lines.append(f"*{dates}*")
                lines.append("")
                for bullet in job.get("achievements", []):
                    lines.append(f"- {bullet}")
                lines.append("")

        # Education
        education = resume.get("education", [])
        if education:
            lines.append("## Education\n")
            for edu in education:
                degree = edu.get("degree", "")
                institution = edu.get("institution", "")
                year = edu.get("year", "")
                lines.append(f"**{degree}** – {institution} ({year})")
            lines.append("")

        # Certifications
        certs = resume.get("certifications", [])
        if certs:
            lines.append("## Certifications\n")
            for cert in certs:
                lines.append(f"- {cert}")
            lines.append("")

        # Projects
        projects = resume.get("projects", [])
        if projects:
            lines.append("## Projects\n")
            for project in projects:
                pname = project.get("name", "")
                pdesc = project.get("description", "")
                purl = project.get("url", "")
                line = f"**{pname}**: {pdesc}"
                if purl:
                    line += f" ([link]({purl}))"
                lines.append(line)
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def to_pdf(self, resume: dict[str, Any], output_path: str) -> str:
        """Export the resume to a PDF file using reportlab.

        Returns the absolute path.  Falls back to Markdown if reportlab
        is not installed.
        """
        try:
            return self._build_pdf(resume, output_path)
        except ImportError:
            logger.warning(
                "reportlab is not installed – exporting as Markdown instead."
            )
            md_path = output_path.replace(".pdf", ".md")
            return self.to_markdown(resume, md_path)

    def _build_pdf(self, resume: dict[str, Any], output_path: str) -> str:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(str(path), pagesize=letter)
        styles = getSampleStyleSheet()
        story: list = []

        # Custom styles
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=4)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, spaceAfter=3)
        h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11, spaceAfter=2)
        normal = styles["Normal"]
        bullet_style = ParagraphStyle(
            "bullet", parent=normal, leftIndent=20, bulletIndent=10, spaceAfter=2
        )

        def add_section(title: str):
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(title, h2))

        # Name
        story.append(Paragraph(resume.get("name", ""), h1))

        # Contact
        contact = resume.get("contact", {})
        contact_line = " | ".join(
            v for v in contact.values() if v
        )
        if contact_line:
            story.append(Paragraph(contact_line, normal))

        # Summary
        if resume.get("summary"):
            add_section("Professional Summary")
            story.append(Paragraph(resume["summary"], normal))

        # Skills
        skills = resume.get("highlighted_skills") or resume.get("skills", [])
        if skills:
            add_section("Skills")
            story.append(Paragraph(", ".join(skills), normal))

        # Experience
        experience = resume.get("experience", [])
        if experience:
            add_section("Experience")
            for job in experience:
                story.append(
                    Paragraph(
                        f"<b>{job.get('title', '')} – {job.get('company', '')}</b>"
                        f"  <i>{job.get('dates', '')}</i>",
                        h3,
                    )
                )
                for bullet in job.get("achievements", []):
                    story.append(Paragraph(f"• {bullet}", bullet_style))
                story.append(Spacer(1, 0.05 * inch))

        # Education
        education = resume.get("education", [])
        if education:
            add_section("Education")
            for edu in education:
                story.append(
                    Paragraph(
                        f"<b>{edu.get('degree', '')}</b> – "
                        f"{edu.get('institution', '')} ({edu.get('year', '')})",
                        normal,
                    )
                )

        # Certifications
        certs = resume.get("certifications", [])
        if certs:
            add_section("Certifications")
            for cert in certs:
                story.append(Paragraph(f"• {cert}", bullet_style))

        doc.build(story)
        logger.info("Resume saved as PDF: %s", path)
        return str(path.resolve())

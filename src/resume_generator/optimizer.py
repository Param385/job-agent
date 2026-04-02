"""
Resume Optimiser.

:class:`ResumeOptimizer` takes a base resume (loaded from JSON) and a job
analysis dict (produced by :class:`~src.jd_analyzer.extractor.JobDescriptionAnalyzer`)
and produces a tailored resume that:

1. Rewrites the professional summary to mirror the job description language.
2. Reorders work-experience entries by relevance to the target role.
3. Highlights skills that overlap with required skills.
4. Enhances achievement bullets to align with the job's key terms.
5. Computes a simple 0-100 match score.

The optimised resume is returned as a plain Python dict so that
:class:`~src.resume_generator.formatters.ResumeFormatter` can export it to
JSON, Markdown, or PDF.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.config import config

logger = logging.getLogger(__name__)


class ResumeOptimizer:
    """Customise a base resume for a specific job.

    Parameters
    ----------
    base_resume_path:
        Path to the JSON file containing the user's base resume.
        Defaults to ``config.base_resume_path``.
    use_ai:
        When ``True`` and an OpenAI API key is configured, GPT-4 is used to
        rewrite the summary and enhance achievement bullets.
    """

    def __init__(
        self,
        base_resume_path: Optional[str] = None,
        use_ai: bool = True,
    ) -> None:
        self.base_resume_path = base_resume_path or config.base_resume_path
        self.use_ai = use_ai
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            from src.ai_engine.llm_client import LLMClient
            self._llm = LLMClient()
        return self._llm

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_base_resume(self) -> dict[str, Any]:
        """Load and return the base resume from the JSON file."""
        path = Path(self.base_resume_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Base resume not found at {path}. "
                "Edit data/base_resume.json with your details."
            )
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def optimize(
        self, job_analysis: dict[str, Any], base_resume: Optional[dict] = None
    ) -> dict[str, Any]:
        """Generate a tailored resume for the analysed job.

        Parameters
        ----------
        job_analysis:
            Output from :meth:`~src.jd_analyzer.extractor.JobDescriptionAnalyzer.analyze`.
        base_resume:
            Optional in-memory resume dict; loaded from disk when ``None``.

        Returns
        -------
        dict
            The customised resume as a structured dictionary.
        """
        if base_resume is None:
            base_resume = self.load_base_resume()

        resume = json.loads(json.dumps(base_resume))  # deep copy

        required_skills = [s.lower() for s in job_analysis.get("skills_required", [])]
        keywords = job_analysis.get("keywords", [])

        # 1. Highlight matching skills
        resume["highlighted_skills"] = self._highlight_skills(resume, required_skills)

        # 2. Reorder experience by relevance
        resume["experience"] = self._reorder_experience(
            resume.get("experience", []), required_skills + keywords
        )

        # 3. Customise the professional summary (AI or rule-based)
        resume["summary"] = self._generate_summary(resume, job_analysis)

        # 4. Enhance achievement bullets
        if self.use_ai:
            resume["experience"] = self._enhance_achievements(
                resume["experience"], job_analysis
            )

        # 5. Compute match score
        resume["match_score"] = self._compute_match_score(resume, required_skills)

        # 6. Attach job metadata
        resume["target_job"] = {
            "title": job_analysis.get("title", ""),
            "company": job_analysis.get("company", ""),
            "experience_level": job_analysis.get("experience_level", ""),
        }

        return resume

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _highlight_skills(resume: dict, required_skills: list[str]) -> list[str]:
        """Return user skills that match the job's required skills."""
        all_user_skills = [s.lower() for s in resume.get("skills", [])]
        return [s for s in resume.get("skills", []) if s.lower() in required_skills]

    @staticmethod
    def _reorder_experience(
        experience: list[dict], keywords: list[str]
    ) -> list[dict]:
        """Sort experience entries by keyword overlap (most relevant first)."""
        def _score(entry: dict) -> int:
            text = json.dumps(entry).lower()
            return sum(1 for kw in keywords if kw.lower() in text)

        return sorted(experience, key=_score, reverse=True)

    def _generate_summary(
        self, resume: dict, job_analysis: dict
    ) -> str:
        """Write a tailored professional summary."""
        if self.use_ai:
            try:
                return self._ai_summary(resume, job_analysis)
            except Exception as exc:
                logger.warning("AI summary failed: %s – using template.", exc)

        # Fallback template
        name = resume.get("name", "I")
        level = job_analysis.get("experience_level", "experienced")
        title = job_analysis.get("title", "professional")
        skills = ", ".join(job_analysis.get("skills_required", [])[:5])
        return (
            f"{name} is an {level} {title} with expertise in {skills}. "
            "Passionate about delivering high-quality solutions and continuous learning."
        )

    def _ai_summary(self, resume: dict, job_analysis: dict) -> str:
        prompt = f"""You are a professional resume writer.

Write a compelling 3-4 sentence professional summary for the candidate below,
tailored to the target job.  Use the job's keywords naturally.  Write in
first person.  Be specific and quantify where possible.

Candidate name: {resume.get("name", "")}
Current title: {resume.get("current_title", "")}
Years of experience: {resume.get("years_experience", "")}
Skills: {", ".join(resume.get("skills", [])[:15])}

Target job title: {job_analysis.get("title", "")}
Target company: {job_analysis.get("company", "")}
Required skills: {", ".join(job_analysis.get("skills_required", [])[:10])}
Key keywords: {", ".join(job_analysis.get("keywords", [])[:8])}

Return ONLY the summary paragraph, no labels, no quotes.
"""
        return self.llm.complete(prompt, temperature=0.7, max_tokens=300)

    def _enhance_achievements(
        self, experience: list[dict], job_analysis: dict
    ) -> list[dict]:
        """Use AI to rewrite achievement bullets to better match the job."""
        keywords = ", ".join(job_analysis.get("keywords", [])[:10])
        if not keywords:
            return experience

        enhanced = []
        for entry in experience:
            achievements = entry.get("achievements", [])
            if achievements:
                try:
                    entry = dict(entry)
                    entry["achievements"] = self._ai_enhance_bullets(
                        achievements, keywords
                    )
                except Exception as exc:
                    logger.debug("Could not enhance achievements: %s", exc)
            enhanced.append(entry)
        return enhanced

    def _ai_enhance_bullets(
        self, bullets: list[str], keywords: str
    ) -> list[str]:
        prompt = f"""You are a professional resume writer.

Rewrite these achievement bullets to better align with the keywords: {keywords}

Rules:
- Keep the same meaning and true facts (don't invent metrics).
- Use strong action verbs.
- Incorporate the keywords naturally where relevant.
- Return ONLY the rewritten bullets as a JSON array of strings.
- Keep exactly the same number of bullets.

Original bullets:
{json.dumps(bullets)}
"""
        raw = self.llm.complete(prompt, temperature=0.5, max_tokens=600)
        import re
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result
        except Exception:
            pass
        return bullets

    @staticmethod
    def _compute_match_score(resume: dict, required_skills: list[str]) -> float:
        """Return a 0-100 match score based on skill overlap."""
        if not required_skills:
            return 50.0
        user_skills = {s.lower() for s in resume.get("skills", [])}
        matched = sum(1 for s in required_skills if s in user_skills)
        return round(matched / len(required_skills) * 100, 1)

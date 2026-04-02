"""
Job Description Analyser.

:class:`JobDescriptionAnalyzer` combines rule-based NLP helpers with
GPT-4 to produce a rich JSON analysis of any job description.

Analysis output schema
----------------------
::

    {
        "title":            "Senior Python Developer",
        "company":          "Acme Corp",
        "experience_level": "senior",
        "years_required":   5,
        "skills_required":  ["Python", "Django", "PostgreSQL", ...],
        "skills_nice":      ["Kubernetes", "React", ...],
        "keywords":         ["REST API", "microservices", ...],
        "responsibilities": ["Design scalable APIs", ...],
        "benefits":         ["Remote", "401k", ...],
        "summary":          "A one-sentence human-readable overview"
    }
"""

import json
import logging
import re
from typing import Any

from src.jd_analyzer.nlp_utils import extract_keywords, extract_skills_simple, infer_experience_level

logger = logging.getLogger(__name__)


class JobDescriptionAnalyzer:
    """Analyse a job description and return structured JSON data.

    Parameters
    ----------
    use_ai:
        When ``True`` (default) and an OpenAI API key is configured, GPT-4
        is used to enrich the analysis.  Set to ``False`` to run entirely
        offline with the rule-based extractors.
    """

    def __init__(self, use_ai: bool = True) -> None:
        self.use_ai = use_ai
        self._llm = None

    @property
    def llm(self):
        """Lazy-load the LLM client to avoid import errors when OpenAI is not set up."""
        if self._llm is None:
            from src.ai_engine.llm_client import LLMClient
            self._llm = LLMClient()
        return self._llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, description: str, title: str = "", company: str = "") -> dict[str, Any]:
        """Analyse *description* and return a structured dict.

        Falls back to rule-based analysis if the AI call fails.
        """
        # Always run the fast rule-based pass first
        base = self._rule_based_analysis(description, title, company)

        if self.use_ai:
            try:
                ai_result = self._ai_analysis(description, title, company)
                # Merge: AI result takes precedence but fill missing keys from base
                for key, value in base.items():
                    if key not in ai_result or not ai_result[key]:
                        ai_result[key] = value
                return ai_result
            except Exception as exc:
                logger.warning(
                    "AI analysis failed (%s) – using rule-based result.", exc
                )

        return base

    # ------------------------------------------------------------------
    # Rule-based analysis (offline, no API key required)
    # ------------------------------------------------------------------

    def _rule_based_analysis(
        self, description: str, title: str, company: str
    ) -> dict[str, Any]:
        skills = extract_skills_simple(description)
        keywords = extract_keywords(description, top_n=15)
        experience_level = infer_experience_level(description)
        years = self._extract_years(description)
        responsibilities = self._extract_responsibilities(description)
        benefits = self._extract_benefits(description)

        return {
            "title": title,
            "company": company,
            "experience_level": experience_level,
            "years_required": years,
            "skills_required": skills,
            "skills_nice": [],
            "keywords": keywords,
            "responsibilities": responsibilities,
            "benefits": benefits,
            "summary": f"{title} at {company}. Requires {experience_level}-level experience."
            if title
            else "",
        }

    @staticmethod
    def _extract_years(text: str) -> int:
        m = re.search(r"(\d+)\+?\s*years?", text, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _extract_responsibilities(text: str) -> list[str]:
        """Heuristically pull bullet-point responsibilities from the text."""
        bullets: list[str] = []
        for line in text.splitlines():
            line = line.strip().lstrip("-•*·▪▸►●○◦")
            line = line.strip()
            if 20 < len(line) < 200:
                # Likely a bullet if it starts with a verb or is a short sentence
                first_word = line.split()[0].lower() if line.split() else ""
                ACTION_VERBS = {
                    "design", "develop", "build", "create", "implement", "maintain",
                    "collaborate", "work", "write", "manage", "lead", "own",
                    "ensure", "support", "analyse", "analyze", "review", "drive",
                }
                if first_word in ACTION_VERBS:
                    bullets.append(line)
        return bullets[:10]

    @staticmethod
    def _extract_benefits(text: str) -> list[str]:
        """Look for common benefits in the description text."""
        BENEFIT_KEYWORDS = [
            "remote", "flexible", "401k", "health insurance", "dental",
            "vision", "pto", "vacation", "equity", "stock", "bonus",
            "unlimited pto", "parental leave", "learning budget",
        ]
        lower = text.lower()
        return [b for b in BENEFIT_KEYWORDS if b in lower]

    # ------------------------------------------------------------------
    # AI-enhanced analysis
    # ------------------------------------------------------------------

    def _ai_analysis(
        self, description: str, title: str, company: str
    ) -> dict[str, Any]:
        """Use GPT-4 to extract structured job requirements."""
        prompt = self._build_prompt(description, title, company)
        raw = self.llm.complete(prompt, temperature=0.2)

        # GPT sometimes wraps JSON in markdown code fences – strip them
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Could not parse AI JSON response: %s\nRaw: %s", exc, raw[:200])
            raise

    @staticmethod
    def _build_prompt(description: str, title: str, company: str) -> str:
        return f"""You are an expert recruiter and technical analyst.

Analyse the following job description and return a JSON object with **exactly** these keys:

{{
  "title": "<job title>",
  "company": "<company name>",
  "experience_level": "<junior|mid|senior>",
  "years_required": <integer years of experience, 0 if not specified>,
  "skills_required": ["<skill1>", "<skill2>", ...],
  "skills_nice": ["<nice-to-have skill>", ...],
  "keywords": ["<keyword1>", ...],
  "responsibilities": ["<responsibility1>", ...],
  "benefits": ["<benefit1>", ...],
  "summary": "<one sentence overview>"
}}

Rules:
- Return ONLY valid JSON, no markdown fences, no extra text.
- skills_required: Must-have technical skills extracted verbatim.
- skills_nice: "preferred" or "bonus" skills.
- keywords: Important domain terms/technologies (up to 15).
- responsibilities: Key duties as concise action-phrases (up to 8).
- benefits: Company perks mentioned.

Job Title: {title}
Company: {company}

Job Description:
{description[:4000]}
"""

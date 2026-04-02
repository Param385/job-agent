"""
OpenAI GPT-4 API wrapper.

:class:`LLMClient` is the single point of contact with the OpenAI API.
All other modules that need language-model capabilities should import and
use this class rather than calling ``openai`` directly.

Features
--------
* Validates that ``OPENAI_API_KEY`` is set before making calls.
* Supports both chat-completion (GPT-4) and legacy completion endpoints.
* Retry on transient API errors with exponential back-off.
* Token-usage logging so you can keep track of costs.
* Simple ``complete()`` convenience method used throughout the project.

Usage::

    from src.ai_engine.llm_client import LLMClient
    llm = LLMClient()
    response = llm.complete("Write a short professional summary for a Python developer.")
    print(response)
"""

import logging
from typing import Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around the OpenAI chat completion API.

    Parameters
    ----------
    api_key:
        Override the key from ``config.openai_api_key`` (useful in tests).
    model:
        Override the model from ``config.openai_model``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or config.openai_api_key
        self.model = model or config.openai_model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is not set. "
                "Add OPENAI_API_KEY=<your-key> to your .env file or environment."
            )

        import openai  # noqa: PLC0415 – deferred to avoid hard dependency at import time
        self._client = openai.OpenAI(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def complete(
        self,
        prompt: str,
        system_message: str = "You are a helpful assistant specialising in career coaching and technical recruitment.",
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
    ) -> str:
        """Send a single-turn prompt and return the assistant's reply as a string.

        Parameters
        ----------
        prompt:
            The user message / instruction.
        system_message:
            Optional system role instructions.
        temperature:
            Sampling temperature (0 = deterministic, 1 = creative).
            Defaults to ``config.openai_temperature``.
        max_tokens:
            Maximum tokens in the response.

        Returns
        -------
        str
            The text of the model's reply.
        """
        if temperature is None:
            temperature = config.openai_temperature

        logger.debug("LLM request | model=%s | tokens_limit=%d", self.model, max_tokens)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        logger.info(
            "LLM usage | prompt=%d | completion=%d | total=%d tokens",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
        )

        return response.choices[0].message.content.strip()

    def chat(self, messages: list[dict]) -> str:
        """Send a multi-turn conversation and return the last assistant message.

        Parameters
        ----------
        messages:
            List of ``{"role": ..., "content": ...}`` dicts following the
            OpenAI Chat format.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=config.openai_temperature,
        )
        return response.choices[0].message.content.strip()

    def generate_json(self, prompt: str) -> str:
        """Convenience wrapper that instructs the model to return pure JSON."""
        system = (
            "You are a data extraction assistant. "
            "Always respond with valid JSON only, no markdown fences, no extra text."
        )
        return self.complete(prompt, system_message=system, temperature=0.1)

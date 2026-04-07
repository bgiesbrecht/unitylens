"""LLM client wrapper for Databricks Model Serving endpoints."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 2048


class LLMClient:
    """Thin wrapper around a Databricks Model Serving chat/completions endpoint.

    Parameters
    ----------
    endpoint_url:
        Full URL to the serving endpoint, e.g.
        ``https://myws.cloud.databricks.com/serving-endpoints/my-llm/invocations``
    token:
        Databricks personal access token or service principal token.
    max_tokens:
        Maximum tokens in the response.
    temperature:
        Sampling temperature.
    """

    def __init__(
        self,
        endpoint_url: str,
        token: str,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.1,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.token = token
        self.max_tokens = max_tokens
        self.temperature = temperature

    def send_query(
        self,
        question: str,
        context: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a question with metadata context to the LLM.

        Parameters
        ----------
        question:
            The user's natural-language question.
        context:
            Metadata context string (from the context builder).
        system_prompt:
            Optional system prompt override.

        Returns
        -------
        str
            The model's response text.
        """
        if system_prompt is None:
            system_prompt = (
                "You are UnityLens, a metadata search assistant. "
                "You help users find tables, columns, and schemas across "
                "multiple data platforms. Use the following metadata context "
                "to answer questions accurately. If you cannot find a match, "
                "say so clearly.\n\n"
                f"METADATA CONTEXT:\n{context}"
            )

        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        logger.debug("Sending LLM query: %s", question[:100])

        try:
            resp = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()

            # Handle both OpenAI-compatible and Databricks response formats
            choices = body.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "").strip()

            # Fallback: some endpoints return predictions directly
            predictions = body.get("predictions", [])
            if predictions:
                return str(predictions[0]).strip()

            logger.warning("Unexpected LLM response structure: %s", list(body.keys()))
            return "Unable to parse LLM response."

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return "The LLM request timed out. Please try again."
        except requests.exceptions.HTTPError as exc:
            logger.error("LLM HTTP error: %s", exc)
            return f"LLM service returned an error: {exc.response.status_code}"
        except Exception as exc:
            logger.exception("Unexpected error calling LLM")
            return f"An error occurred while querying the LLM: {exc}"


# Module-level singleton (initialized lazily from settings)
_client: LLMClient | None = None


def get_llm_client() -> LLMClient | None:
    """Return the module-level LLM client, or None if not configured."""
    return _client


def init_llm_client(
    endpoint_url: str,
    token: str,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    temperature: float = 0.1,
) -> LLMClient:
    """Initialize the module-level LLM client."""
    global _client
    _client = LLMClient(
        endpoint_url=endpoint_url,
        token=token,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    logger.info("LLM client initialized (endpoint=%s)", endpoint_url)
    return _client

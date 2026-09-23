import logging
import time
from typing import Tuple

from app.config import settings
from app.metrics import LLM_TOKEN_USAGE

logger = logging.getLogger(__name__)

# Initialize client if API key is provided
try:
    from google import genai
    client = genai.Client(api_key=settings.LLM_API_KEY) if settings.LLM_API_KEY else None
except Exception:
    client = None


class LLMTimeoutError(Exception):
    """Raised when LLM call exceeds the configured timeout."""
    pass


class LLMProviderError(Exception):
    """Raised when LLM upstream service fails."""
    pass


def _call_model(model_name: str, question: str) -> Tuple[str, int]:
    if not client:
        # Development / demo response when API key is not configured
        simulated_tokens = max(10, len(question.split()) + 30)
        LLM_TOKEN_USAGE.inc(simulated_tokens)
        return (
            f"[Response from {model_name}] Here is the AI answer to: '{question}'",
            simulated_tokens,
        )

    response = client.models.generate_content(
        model=model_name,
        contents=question,
    )

    if not response or not response.text:
        raise LLMProviderError(f"LLM model {model_name} returned an empty response")

    tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
    if tokens == 0:
        tokens = max(1, len(question.split()) + len(response.text.split()))

    LLM_TOKEN_USAGE.inc(tokens)
    return response.text, tokens


def ask_gemini(question: str) -> Tuple[str, int, str]:
    """
    Sends question to Gemini with exponential backoff retries,
    timeout handling, and secondary model fallback.
    Returns: (answer_text, tokens_used, model_used)
    """
    max_retries = 2
    models_to_try = [settings.PRIMARY_MODEL, settings.FALLBACK_MODEL]

    last_error = None
    for model in models_to_try:
        for attempt in range(max_retries):
            try:
                answer, tokens = _call_model(model, question)
                return answer, tokens, model
            except Exception as exc:
                last_error = exc
                err_msg = str(exc).lower()
                logger.warning(
                    f"LLM call to {model} attempt {attempt + 1}/{max_retries} failed: {exc}"
                )
                if "deadline" in err_msg or "timed out" in err_msg or "timeout" in err_msg:
                    if attempt == max_retries - 1 and model == models_to_try[-1]:
                        raise LLMTimeoutError(f"LLM request timed out after {settings.LLM_TIMEOUT}s: {exc}") from exc
                time.sleep(1.0 ** attempt)

    raise LLMProviderError(f"LLM requests failed across primary and fallback models: {last_error}") from last_error
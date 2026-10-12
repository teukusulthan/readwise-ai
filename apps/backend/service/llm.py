"""
LLM access: an Agno Agent backed by Agno's LiteLLM model class (verified on agno 3.0.10).

LiteLLM routes one model string to many providers, e.g. "openai/gpt-4o-mini",
"anthropic/claude-...", "openrouter/<model>", or any OpenAI-compatible server via
LLM_API_BASE. Configure with BE_LLM_MODEL / BE_LLM_API_KEY / BE_LLM_API_BASE.
"""

from typing import Optional

from loguru import logger

from config.base import settings
from util.http_errors import ServiceUnavailableError


def _is_error(output) -> bool:
    status = getattr(output, "status", None)
    return str(getattr(status, "value", status)).upper() == "ERROR"


def _user_message(detail: str) -> str:
    """Short, actionable message without provider internals."""
    if "AuthenticationError" in detail or "401" in detail:
        return "The language model rejected the API key. Check BE_LLM_API_KEY."
    if "RateLimitError" in detail or "429" in detail:
        return "The language model is rate-limited right now. Try again shortly."
    if "NotFoundError" in detail or "404" in detail:
        return "The configured language model was not found. Check BE_LLM_MODEL."
    return "The language model request failed. See server logs for details."


def _model(request_params: Optional[dict] = None):
    from agno.models.litellm import LiteLLM

    return LiteLLM(
        id=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY or None,
        api_base=settings.LLM_API_BASE or None,
        # None = not sent (Agno drops None values), so the provider default applies. Needed for models with
        # fixed sampling, e.g. Kimi Code (only temperature 1 / top_p 0.95) and many reasoning models —
        # Agno would otherwise send its own defaults (temperature 0.7, top_p 1.0).
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        max_tokens=settings.LLM_MAX_TOKENS,
        request_params=request_params,
    )


def agno_generator(request_params: Optional[dict] = None):
    """Return `generate(system_prompt, user_prompt) -> answer text`."""
    if not settings.LLM_MODEL:
        raise ServiceUnavailableError("No LLM configured (set BE_LLM_MODEL).")

    from agno.agent import Agent

    def generate(system_prompt: str, user_prompt: str) -> str:
        agent = Agent(
            model=_model(request_params),
            system_message=system_prompt,
            markdown=False,
            telemetry=False,  # don't send usage data to Agno
        )
        try:
            output = agent.run(user_prompt)
        except Exception as error:
            raise ServiceUnavailableError(f"The language model request failed ({type(error).__name__}).") from error

        content = getattr(output, "content", None)
        # Agno does not raise on provider errors (bad key, rate limit, unknown model): it returns a
        # RunOutput with status=ERROR and the error text as `content`. Never show that as an answer.
        if _is_error(output):
            logger.error("LLM request failed ({model}): {detail}", model=settings.LLM_MODEL, detail=str(content)[:500])
            raise ServiceUnavailableError(_user_message(str(content or "")))
        return content if isinstance(content, str) else str(content or "")

    return generate


def agno_streamer(request_params: Optional[dict] = None):
    """
    Return `stream(system_prompt, user_prompt) -> async iterator of answer text pieces`.

    Only the answer text is yielded. Reasoning models (e.g. Nemotron) first emit
    "thinking" in `reasoning_content` with empty `content`; that is never forwarded.
    Agno reports provider failures mid-stream as a RunErrorEvent (not an exception),
    which is converted into ServiceUnavailableError here.
    """
    if not settings.LLM_MODEL:
        raise ServiceUnavailableError("No LLM configured (set BE_LLM_MODEL).")

    from agno.agent import Agent

    async def stream(system_prompt: str, user_prompt: str):
        agent = Agent(
            model=_model(request_params),
            system_message=system_prompt,
            markdown=False,
            telemetry=False,
        )
        try:
            async for event in agent.arun(user_prompt, stream=True):
                content = getattr(event, "content", None)
                if type(event).__name__ == "RunErrorEvent" or _is_error(event):
                    logger.error("LLM stream failed ({model}): {detail}", model=settings.LLM_MODEL,
                                 detail=str(content)[:500])
                    raise ServiceUnavailableError(_user_message(str(content or "")))
                if type(event).__name__ == "RunContentEvent" and isinstance(content, str) and content:
                    yield content
        except ServiceUnavailableError:
            raise
        except Exception as error:
            logger.exception("LLM stream crashed")
            raise ServiceUnavailableError(f"The language model request failed ({type(error).__name__}).") from error

    return stream

"""OpenAI client wrappers — all LLM access in the project goes through here.

Wraps `langchain-openai` with:
  - Langfuse callbacks (if configured)
  - Prometheus token + latency tracking
  - Tenacity retry on transient errors
  - Structured-output helpers using Pydantic
"""

from __future__ import annotations

import time
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, SecretStr
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...config import get_settings
from ...observability.logger import get_logger
from ...observability.metrics import (
    errors_total,
    llm_call_duration_seconds,
    openai_tokens_total,
)
from ...observability.tracer import callback_list

_log = get_logger(__name__)
_T = TypeVar("_T", bound=BaseModel)

# Lazy singletons.
_HEAVY: ChatOpenAI | None = None
_LIGHT: ChatOpenAI | None = None
_EMB: OpenAIEmbeddings | None = None


def _make_chat(model: str) -> ChatOpenAI:
    s = get_settings()
    if s.llm_provider == "ollama":
        # Ollama on a single GPU is much slower than OpenAI cloud.
        # Generous timeout (3 min) and few retries to avoid thundering herd.
        return ChatOpenAI(
            model=model,
            api_key=SecretStr("ollama"),
            base_url=s.llm_base_url or "http://host.docker.internal:11434/v1",
            timeout=max(s.global_request_timeout_seconds, 180),
            max_retries=1,
        )
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(s.openai_api_key),
        base_url=s.llm_base_url or None,
        timeout=s.global_request_timeout_seconds,
        max_retries=4,
    )


def _make_embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    if s.embedding_provider == "ollama":
        return OpenAIEmbeddings(
            model=s.openai_embedding_model,
            api_key=SecretStr("ollama"),
            base_url=s.embedding_base_url or "http://host.docker.internal:11434/v1",
            check_embedding_ctx_length=False,
        )
    return OpenAIEmbeddings(
        model=s.openai_embedding_model,
        api_key=SecretStr(s.openai_api_key),
        base_url=s.embedding_base_url or None,
    )


def heavy_llm() -> ChatOpenAI:
    global _HEAVY
    if _HEAVY is None:
        _HEAVY = _make_chat(get_settings().openai_model_heavy)
    return _HEAVY


def light_llm() -> ChatOpenAI:
    global _LIGHT
    if _LIGHT is None:
        _LIGHT = _make_chat(get_settings().openai_model_light)
    return _LIGHT


def embeddings() -> OpenAIEmbeddings:
    global _EMB
    if _EMB is None:
        _EMB = _make_embeddings()
    return _EMB


def _track_usage(model: str, response: BaseMessage, started_at: float) -> None:
    duration = time.monotonic() - started_at
    llm_call_duration_seconds.labels(model=model).observe(duration)
    usage = (response.response_metadata or {}).get("token_usage", {}) if hasattr(response, "response_metadata") else {}
    if usage:
        openai_tokens_total.labels(model=model, kind="prompt").inc(usage.get("prompt_tokens", 0))
        openai_tokens_total.labels(model=model, kind="completion").inc(usage.get("completion_tokens", 0))


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
)
async def chat(
    messages: list[BaseMessage],
    *,
    use_heavy: bool = False,
    response_format: type[_T] | None = None,
) -> _T | str:
    """Async chat with retry, telemetry, and optional structured output.

    Returns either:
      - the parsed Pydantic model instance if `response_format` is given, OR
      - the raw `.content` string if not.
    """
    llm = heavy_llm() if use_heavy else light_llm()
    model_name = get_settings().openai_model_heavy if use_heavy else get_settings().openai_model_light
    started = time.monotonic()
    try:
        if response_format is not None:
            structured = llm.with_structured_output(response_format)
            result = await structured.ainvoke(messages, config={"callbacks": callback_list()})
            return result  # type: ignore[return-value]
        msg = await llm.ainvoke(messages, config={"callbacks": callback_list()})
        _track_usage(model_name, msg, started)
        return msg.content if isinstance(msg.content, str) else str(msg.content)
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="llm", category=type(e).__name__).inc()
        _log.warning("openai.call_failed", model=model_name, error=str(e))
        raise


async def embed_one(text: str) -> list[float]:
    return await embeddings().aembed_query(text)


async def embed_many(texts: list[str]) -> list[list[float]]:
    return await embeddings().aembed_documents(texts)


async def warmup() -> None:
    """Best-effort warm-up: load the Ollama model into VRAM before the first
    real call so we don't pay 10-30s cold-start latency on a parallel burst.
    No-op for OpenAI (the API has no cold-start)."""
    s = get_settings()
    if s.llm_provider != "ollama":
        return
    from langchain_core.messages import HumanMessage

    for label, llm in (("light", light_llm()), ("heavy", heavy_llm())):
        try:
            await llm.ainvoke([HumanMessage(content="ping")], config={"callbacks": []})
            _log.info("ollama.warmup_ok", model=label)
        except Exception as e:  # noqa: BLE001
            _log.warning("ollama.warmup_failed", model=label, error=str(e))

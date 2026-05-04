"""LLM client wrapper — single entry point for chat + embeddings.

The crawler swaps providers via `Settings.llm_provider`:

  - `openai`  → `langchain-openai` ChatOpenAI / OpenAIEmbeddings (cloud, paid).
  - `ollama`  → `langchain-ollama` ChatOllama / OllamaEmbeddings (local, free).
                The Ollama path uses `with_structured_output(method="json_schema")`
                which constrains decoding to the Pydantic schema and is far
                more reliable than letting a small model free-form JSON.

Every agent in the codebase calls `chat()` / `embed_one()` / `embed_many()`
without caring which backend is active, so switching providers is a one-line
config change (plus pulling the model on the local Ollama daemon).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, SecretStr, ValidationError
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

# Lazy singletons. Heavy/light only differ for cloud OpenAI; on Ollama we run
# one model for everything (granite4.1:3b) to keep VRAM use predictable.
_HEAVY: Any = None
_LIGHT: Any = None
_EMB: Any = None


def _is_ollama() -> bool:
    return get_settings().llm_provider.lower() == "ollama"


def _is_groq() -> bool:
    return get_settings().llm_provider.lower() == "groq"


def _is_ollama_embedding() -> bool:
    return get_settings().embedding_provider.lower() == "ollama"


def _ollama_base_url(default: str = "http://ollama:11434") -> str:
    """ChatOllama wants the bare base, not the /v1 path that ChatOpenAI uses."""
    s = get_settings()
    raw = s.llm_base_url or default
    return raw.rstrip("/").removesuffix("/v1")


def _ollama_embedding_base_url(default: str = "http://ollama:11434") -> str:
    s = get_settings()
    raw = s.embedding_base_url or default
    return raw.rstrip("/").removesuffix("/v1")


def _make_chat(model: str) -> Any:
    s = get_settings()
    if _is_ollama():
        # langchain-ollama gives us native Ollama API access (better than the
        # openai-compat shim) plus structured output via `format=json_schema`.
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=_ollama_base_url(),
            temperature=0.0,
            num_ctx=16384,
        )
    if _is_groq():
        # Groq is OpenAI-compatible, so reuse ChatOpenAI with a base_url override.
        # Free tier rate limits live on the Groq dashboard; if you blow them
        # we get HTTP 429 which tenacity in chat() retries.
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(s.groq_api_key or "missing-groq-key"),
            base_url=s.groq_base_url or "https://api.groq.com/openai/v1",
            timeout=s.global_request_timeout_seconds,
            max_retries=2,
            temperature=0.0,
        )
    # OpenAI cloud path (escape hatch).
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(s.openai_api_key),
        base_url=s.llm_base_url or None,
        timeout=s.global_request_timeout_seconds,
        max_retries=4,
    )


def _make_embeddings() -> Any:
    s = get_settings()
    if _is_ollama_embedding():
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=s.openai_embedding_model,
            base_url=_ollama_embedding_base_url(),
        )
    return OpenAIEmbeddings(
        model=s.openai_embedding_model,
        api_key=SecretStr(s.openai_api_key),
        base_url=s.embedding_base_url or None,
    )


def heavy_llm() -> Any:
    global _HEAVY
    if _HEAVY is None:
        _HEAVY = _make_chat(get_settings().openai_model_heavy)
    return _HEAVY


def light_llm() -> Any:
    global _LIGHT
    if _LIGHT is None:
        _LIGHT = _make_chat(get_settings().openai_model_light)
    return _LIGHT


def embeddings() -> Any:
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


async def _chat_structured_with_retry(
    llm: Any,
    messages: list[BaseMessage],
    response_format: type[_T],
    *,
    max_attempts: int = 3,
) -> _T:
    """Drive a structured-output chat with Pydantic validation retries.

    Small local models (granite-3B, llama3-8B etc.) occasionally emit JSON that
    parses but fails Pydantic validation (missing field, wrong type). Retrying
    once or twice with the same schema almost always recovers because the model
    decoder samples differently.
    """
    # Pick the right structured-output method per provider.
    # Ollama uses langchain-ollama json_schema (constrained decoding).
    # Groq + OpenAI use function_calling (tool calling) which hits the
    # /v1/chat/completions endpoint with tools. Avoids the Responses API
    # route that langchain-openai now defaults to (Groq returns 404 there
    # because /v1/responses doesn't exist on their side).
    if _is_ollama():
        method = "json_schema"
    else:
        method = "function_calling"
    last_err: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            structured = llm.with_structured_output(response_format, method=method)
            result = await structured.ainvoke(messages, config={"callbacks": callback_list()})
            if isinstance(result, response_format):
                return result
            # langchain may return a dict if validation succeeds but instance
            # construction was skipped — rebuild explicitly.
            if isinstance(result, dict):
                return response_format.model_validate(result)
            return result  # type: ignore[return-value]
        except ValidationError as e:
            last_err = e
            _log.warning(
                "llm.structured_validation_retry",
                attempt=attempt,
                error=str(e)[:200],
            )
            if attempt >= max_attempts:
                raise
            await asyncio.sleep(0.4 * attempt)
        except Exception as e:  # noqa: BLE001
            # Network / timeout / unparseable JSON. Retry up to max_attempts.
            last_err = e
            _log.warning(
                "llm.structured_call_retry",
                attempt=attempt,
                error=str(e)[:200],
            )
            if attempt >= max_attempts:
                raise
            await asyncio.sleep(0.6 * attempt)

    # Defensive: should never hit (loop either returned or raised).
    if last_err:
        raise last_err
    raise RuntimeError("structured chat exhausted retries without producing a result")


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
    """Async chat with retry, telemetry, and optional structured output."""
    llm = heavy_llm() if use_heavy else light_llm()
    settings = get_settings()
    model_name = settings.openai_model_heavy if use_heavy else settings.openai_model_light
    started = time.monotonic()
    try:
        if response_format is not None:
            return await _chat_structured_with_retry(llm, messages, response_format)
        msg = await llm.ainvoke(messages, config={"callbacks": callback_list()})
        _track_usage(model_name, msg, started)
        return msg.content if isinstance(msg.content, str) else str(msg.content)
    except Exception as e:  # noqa: BLE001
        errors_total.labels(stage="llm", category=type(e).__name__).inc()
        _log.warning("llm.call_failed", model=model_name, error=str(e))
        raise


async def embed_one(text: str) -> list[float]:
    return await embeddings().aembed_query(text)


async def embed_many(texts: list[str]) -> list[list[float]]:
    return await embeddings().aembed_documents(texts)


async def warmup() -> None:
    """Best-effort warm-up. Only matters for Ollama (loads models into VRAM
    before first parallel burst). Groq + OpenAI have no cold-start so we skip."""
    if not _is_ollama():
        return
    from langchain_core.messages import HumanMessage

    for label, llm in (("light", light_llm()), ("heavy", heavy_llm())):
        try:
            await llm.ainvoke([HumanMessage(content="ping")], config={"callbacks": []})
            _log.info("ollama.warmup_ok", model=label)
        except Exception as e:  # noqa: BLE001
            _log.warning("ollama.warmup_failed", model=label, error=str(e))

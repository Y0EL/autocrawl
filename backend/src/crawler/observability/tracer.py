"""Langfuse tracer integration (self-hosted, free).

Returns a LangChain callback handler when langfuse is configured. Otherwise
returns None — the rest of the app silently runs without tracing.
"""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from .logger import get_logger

_log = get_logger(__name__)
_HANDLER: Any | None = None
_INITIALIZED = False


def get_langfuse_handler() -> Any | None:
    """Idempotent. Returns a LangChain `CallbackHandler` instance or None."""
    global _HANDLER, _INITIALIZED
    if _INITIALIZED:
        return _HANDLER

    settings = get_settings()
    _INITIALIZED = True

    if not settings.langfuse_enabled:
        _log.info("langfuse.disabled_via_setting")
        return None

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        _log.info("langfuse.not_configured", hint="set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
        return None

    # langfuse v2: `from langfuse.callback import CallbackHandler`
    # langfuse v3: `from langfuse.langchain import CallbackHandler`
    CallbackHandler = None
    try:
        from langfuse.callback import CallbackHandler  # type: ignore
    except ImportError:
        try:
            from langfuse.langchain import CallbackHandler  # type: ignore
        except ImportError as e:
            _log.warning("langfuse.import_failed", error=str(e))
            return None

    try:
        _HANDLER = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        _log.info("langfuse.enabled", host=settings.langfuse_host)
        return _HANDLER
    except Exception as e:  # noqa: BLE001
        _log.warning("langfuse.init_failed", error=str(e))
        _HANDLER = None
        return None


def callback_list() -> list:
    """Convenience: returns [handler] or [] for safe `callbacks=` argument."""
    h = get_langfuse_handler()
    return [h] if h is not None else []

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..db.engine import dispose_engine, init_db
from ..observability.logger import configure_logging, get_logger
from .routes import expos, health, overview, pdfs, runs, vendors

_log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    configure_logging()
    last_err: str | None = None
    for attempt in range(1, 11):
        try:
            await init_db()
            _log.info("api.db_init_ok", attempt=attempt)
            last_err = None
            break
        except Exception as e:
            last_err = str(e)
            _log.warning("api.db_init_retry", attempt=attempt, error=last_err)
            await asyncio.sleep(min(2 ** attempt, 15))
    if last_err is not None:
        _log.error("api.db_init_failed_giving_up", error=last_err)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="AutoCrawl API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api")
    application.include_router(overview.router, prefix="/api")
    application.include_router(vendors.router, prefix="/api")
    application.include_router(expos.router, prefix="/api")
    application.include_router(pdfs.router, prefix="/api")
    application.include_router(runs.router, prefix="/api")

    return application


app = create_app()

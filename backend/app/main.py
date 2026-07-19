from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import settings
from app.api.ops import router as operations_router
from app.api.router import api_router
from app.database.session import dispose_engine
from app.runtime.collection_runner import CollectionRunner
from app.runtime.collection_scheduler import CollectionScheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_collection_scheduler() -> CollectionScheduler:
    return CollectionScheduler(
        runner=CollectionRunner(),
        interval_minutes=settings.COLLECTION_INTERVAL_MINUTES,
        run_on_startup=settings.COLLECTION_RUN_ON_STARTUP,
        misfire_grace_seconds=settings.SCHEDULER_MISFIRE_GRACE_SECONDS,
        shutdown_grace_seconds=settings.SHUTDOWN_GRACE_SECONDS,
        instance_id=settings.AEROC_INSTANCE_ID,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    try:
        app.state.process_role = settings.AEROC_PROCESS_ROLE

        if settings.scheduler_enabled:
            scheduler = create_collection_scheduler()
            scheduler.start()
            app.state.collection_scheduler = scheduler

        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown()
        dispose_engine()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(operations_router)

